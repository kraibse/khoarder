import re
import uuid

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.relation import Relation
from app.models.tag import Tag, entry_tags
from app.schemas.entry import ArticleDetailOut, BacklinkOut, EntryOut, EntryUpdate, RelatedEntryOut
from app.schemas.attachment import AttachmentOut


def _format_date(dt) -> str:
    return dt.strftime("%b %d, %Y") if dt else ""


def _entry_source(entry: Entry) -> str | None:
    return entry.source_label or entry.source_url or None


async def _backlink_count(db: AsyncSession, entry_id: str) -> int:
    result = await db.execute(
        select(func.count()).where(Relation.to_entry_id == entry_id, Relation.kind == "backlink")
    )
    return result.scalar_one()


async def _to_entry_out(db: AsyncSession, entry: Entry, headline: str | None = None) -> EntryOut:
    return EntryOut(
        id=entry.id,
        topic_id=entry.topic_id,
        type=entry.type,
        title=entry.title,
        excerpt=entry.excerpt,
        tags=[t.name for t in entry.tags],
        date=_format_date(entry.created_at),
        source=_entry_source(entry),
        has_img=entry.has_img,
        img_url=entry.img_url,
        img_height=entry.img_height,
        img_color=entry.img_color,
        is_starred=entry.is_starred,
        backlink_count=await _backlink_count(db, entry.id),
        headline=headline,
    )


async def list_entries(
    db: AsyncSession,
    topic_id: str | None = None,
    entry_type: str | None = None,
    sort: str = "date_desc",
    q: str | None = None,
    tag: str | None = None,
) -> list[EntryOut]:
    # Search mode: delegate to pluggable FTS backend
    if q:
        from app.services import search as search_svc

        hits = await search_svc.search(db, q, topic_id=topic_id, entry_type=entry_type)
        out = []
        for entry, headline in hits:
            if tag and not any(t.name == tag for t in entry.tags):
                continue
            out.append(await _to_entry_out(db, entry, headline=headline))
        if sort == "backlinks_desc":
            out.sort(key=lambda e: e.backlink_count, reverse=True)
        return out

    # Browse mode: standard ordered query
    stmt = select(Entry).options(selectinload(Entry.tags))

    if topic_id:
        stmt = stmt.where(Entry.topic_id == topic_id)
    if entry_type and entry_type.lower() != "all":
        singular = entry_type.rstrip("s")
        stmt = stmt.where(Entry.type.ilike(f"{singular}%"))
    if tag:
        stmt = stmt.join(entry_tags, Entry.id == entry_tags.c.entry_id).join(
            Tag, Tag.id == entry_tags.c.tag_id
        ).where(Tag.name == tag)

    if sort == "date_asc":
        stmt = stmt.order_by(Entry.created_at.asc())
    elif sort == "title_asc":
        stmt = stmt.order_by(Entry.title.asc())
    else:
        stmt = stmt.order_by(Entry.created_at.desc())

    result = await db.execute(stmt)
    entries = result.scalars().all()
    out = [await _to_entry_out(db, e) for e in entries]

    if sort == "backlinks_desc":
        out.sort(key=lambda e: e.backlink_count, reverse=True)

    return out


async def get_entry(db: AsyncSession, entry_id: str) -> ArticleDetailOut | None:
    result = await db.execute(
        select(Entry).options(selectinload(Entry.tags)).where(Entry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return None

    return ArticleDetailOut(
        id=entry.id,
        topic_id=entry.topic_id,
        type=entry.type,
        title=entry.title,
        excerpt=entry.excerpt,
        body=entry.body,
        tags=[t.name for t in entry.tags],
        date=_format_date(entry.created_at),
        source=_entry_source(entry),
        source_url=entry.source_url,
        has_img=entry.has_img,
        img_url=entry.img_url,
        img_height=entry.img_height,
        img_color=entry.img_color,
        word_count=entry.word_count,
        read_time_min=entry.read_time_min,
        backlink_count=await _backlink_count(db, entry.id),
    )


async def get_backlinks(db: AsyncSession, entry_id: str) -> list[BacklinkOut]:
    result = await db.execute(
        select(Relation)
        .options(selectinload(Relation.from_entry).selectinload(Entry.tags))
        .where(Relation.to_entry_id == entry_id, Relation.kind == "backlink")
    )
    relations = result.scalars().all()

    out = []
    for rel in relations:
        e = rel.from_entry
        refs = await _backlink_count(db, e.id)
        out.append(BacklinkOut(id=e.id, relation_id=rel.id, title=e.title, type=e.type, refs=refs))
    return out


async def get_related(db: AsyncSession, entry_id: str) -> list[RelatedEntryOut]:
    result = await db.execute(
        select(Relation)
        .options(selectinload(Relation.to_entry))
        .where(Relation.from_entry_id == entry_id, Relation.kind == "related")
    )
    relations = result.scalars().all()

    out = []
    for rel in relations:
        e = rel.to_entry
        out.append(RelatedEntryOut(id=e.id, relation_id=rel.id, title=e.title, type=e.type, img_color=e.img_color))
    return out


async def get_attachments(db: AsyncSession, entry_id: str) -> list[AttachmentOut]:
    from app.models.attachment import Attachment

    result = await db.execute(
        select(Attachment).where(Attachment.entry_id == entry_id).order_by(Attachment.created_at)
    )
    return [
        AttachmentOut(
            id=a.id,
            filename=a.filename,
            ext=a.ext,
            size_bytes=a.size_bytes,
            created_at=a.created_at,
        )
        for a in result.scalars().all()
    ]


async def list_all_tags(db: AsyncSession) -> list[str]:
    result = await db.execute(select(Tag.name).order_by(Tag.name))
    return list(result.scalars().all())


# Palette for auto-assigning img_color to new entries
_IMG_COLORS = [
    "oklch(72% 0.08 200)", "oklch(65% 0.10 160)", "oklch(68% 0.07 30)",
    "oklch(60% 0.09 280)", "oklch(74% 0.06 80)", "oklch(62% 0.11 320)",
    "oklch(70% 0.08 120)", "oklch(67% 0.09 240)", "oklch(75% 0.05 50)",
    "oklch(63% 0.10 190)", "oklch(71% 0.07 340)", "oklch(66% 0.08 100)",
]


async def _classify_entry(db: AsyncSession, title: str, excerpt: str, body: str) -> tuple[str | None, str | None]:
    """Use LM Studio to classify an entry into a topic. Returns (topic_id, topic_name) or (None, None)."""
    import logging
    from app.core.config import settings
    from app.services import config as config_svc
    from app.models.topic import Topic

    logger = logging.getLogger(__name__)

    base_url = await config_svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    if not base_url or not base_url.strip():
        return None, None

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            base_url=base_url.rstrip("/") + "/",
            api_key="not-needed",
            timeout=float(await config_svc.get_config_value(db, "llm_timeout", default=str(settings.llm_timeout))),
        )
        model = await config_svc.get_config_value(db, "llm_model", default=settings.llm_model)

        # Get existing topics
        topics_result = await db.execute(select(Topic).order_by(Topic.name))
        topics = topics_result.scalars().all()
        topic_list = ", ".join([f"{t.name}" for t in topics]) if topics else "none"

        prompt = (
            f"Classify the following knowledge entry into one of these existing topics: {topic_list}\n\n"
            f"If none fit, suggest a new short topic name (2-3 words).\n\n"
            f"Title: {title}\n"
            f"Excerpt: {excerpt}\n"
            f"Body: {body[:500]}...\n\n"
            f"Respond with ONLY the topic name, nothing else."
        )

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=50,
        )
        raw_content = response.choices[0].message.content
        suggested = raw_content.strip() if raw_content else ""

        if not suggested:
            logger.warning("LM Studio returned empty topic suggestion")
            return None, None

        # Find matching topic (case-insensitive)
        suggested_lower = suggested.lower()
        for t in topics:
            if t.name.lower() == suggested_lower:
                return t.id, t.name

        # Create new topic
        import re
        slug = re.sub(r'[^\w\s-]', '', suggested_lower).strip()
        slug = re.sub(r'[-\s]+', '-', slug)[:64]
        if not slug:
            slug = "topic"
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while True:
            existing = await db.execute(select(Topic).where(Topic.slug == slug))
            if existing.scalar_one_or_none() is None:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        import random
        colors = [
            "oklch(72% 0.08 200)", "oklch(65% 0.10 160)", "oklch(68% 0.07 30)",
            "oklch(60% 0.09 280)", "oklch(74% 0.06 80)", "oklch(62% 0.11 320)",
            "oklch(70% 0.08 120)", "oklch(67% 0.09 240)", "oklch(75% 0.05 50)",
        ]
        new_topic = Topic(
            id=str(uuid.uuid4()),
            slug=slug,
            name=suggested,
            color=random.choice(colors),
            description="",
        )
        db.add(new_topic)
        await db.flush()
        return new_topic.id, new_topic.name
    except Exception as exc:
        logger.warning("Auto-categorization failed: %s", exc)
        return None, None


async def create_entry(
    db: AsyncSession,
    topic_id: str | None,
    entry_type: str,
    title: str,
    excerpt: str = "",
    body: str = "",
    source_url: str | None = None,
    source_label: str | None = None,
    has_img: bool = False,
    img_url: str | None = None,
    is_starred: bool = False,
    tag_names: list[str] | None = None,
) -> ArticleDetailOut:
    # Auto-categorize if no topic provided (treat empty string as null)
    if not topic_id:
        topic_id, _ = await _classify_entry(db, title, excerpt, body)

    entry_id = str(uuid.uuid4())
    color = _IMG_COLORS[int(entry_id.replace("-", ""), 16) % len(_IMG_COLORS)]

    # Compute word count and read time
    word_count = len(body.split()) if body else 0
    read_time = max(1, round(word_count / 200))

    entry = Entry(
        id=entry_id,
        topic_id=topic_id,
        type=entry_type,
        title=title,
        excerpt=excerpt,
        body=body,
        word_count=word_count,
        read_time_min=read_time,
        has_img=has_img,
        img_url=img_url,
        img_color=color,
        is_starred=is_starred,
        source_url=source_url,
        source_label=source_label,
    )
    db.add(entry)
    await db.flush()

    for tag_name in (tag_names or []):
        tag_result = await db.execute(select(Tag).where(Tag.name == tag_name))
        tag = tag_result.scalar_one_or_none()
        if tag is None:
            tag = Tag(id=str(uuid.uuid4()), name=tag_name)
            db.add(tag)
            await db.flush()
        await db.execute(insert(entry_tags).values(entry_id=entry.id, tag_id=tag.id))

    await db.commit()
    await db.refresh(entry)

    return ArticleDetailOut(
        id=entry.id,
        topic_id=entry.topic_id,
        type=entry.type,
        title=entry.title,
        excerpt=entry.excerpt,
        body=entry.body,
        tags=tag_names or [],
        date=_format_date(entry.created_at),
        source=_entry_source(entry),
        source_url=entry.source_url,
        has_img=entry.has_img,
        img_url=entry.img_url,
        img_height=entry.img_height,
        img_color=entry.img_color,
        is_starred=entry.is_starred,
        word_count=entry.word_count,
        read_time_min=entry.read_time_min,
        backlink_count=0,
    )


async def add_attachment(
    db: AsyncSession,
    entry_id: str,
    filename: str,
    ext: str,
    size_bytes: int,
    storage_path: str,
) -> "AttachmentOut":
    from app.models.attachment import Attachment
    from app.schemas.attachment import AttachmentOut

    att = Attachment(
        id=str(uuid.uuid4()),
        entry_id=entry_id,
        filename=filename,
        ext=ext,
        size_bytes=size_bytes,
        storage_path=storage_path,
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return AttachmentOut(id=att.id, filename=att.filename, ext=att.ext, size_bytes=att.size_bytes, created_at=att.created_at)


async def remove_attachment(db: AsyncSession, attachment_id: str) -> str | None:
    """Delete attachment DB record; return storage_path so caller can remove the file."""
    from app.models.attachment import Attachment

    result = await db.execute(select(Attachment).where(Attachment.id == attachment_id))
    att = result.scalar_one_or_none()
    if att is None:
        return None
    path = att.storage_path
    await db.delete(att)
    await db.commit()
    return path


# ── Phase 5 additions ─────────────────────────────────────────────────────────

async def _sync_tags(db: AsyncSession, entry: Entry, tag_names: list[str]) -> None:
    """Replace the entry's tag associations with the given list (find-or-create tags)."""
    await db.execute(delete(entry_tags).where(entry_tags.c.entry_id == entry.id))
    for tag_name in tag_names:
        tag_result = await db.execute(select(Tag).where(Tag.name == tag_name))
        tag = tag_result.scalar_one_or_none()
        if tag is None:
            tag = Tag(id=str(uuid.uuid4()), name=tag_name)
            db.add(tag)
            await db.flush()
        await db.execute(insert(entry_tags).values(entry_id=entry.id, tag_id=tag.id))


async def detect_and_store_backlinks(db: AsyncSession, entry: Entry) -> None:
    """Scan entry body for [[Title]] and create backlink relations to matching entries."""
    titles = re.findall(r"\[\[(.+?)\]\]", entry.body or "")
    # Remove old auto-detected backlinks from this entry
    await db.execute(
        delete(Relation).where(Relation.from_entry_id == entry.id, Relation.kind == "backlink")
    )
    if not titles:
        return
    for title in set(titles):
        result = await db.execute(
            select(Entry).where(
                Entry.topic_id == entry.topic_id,
                func.lower(Entry.title) == title.lower(),
                Entry.id != entry.id,
            )
        )
        target = result.scalar_one_or_none()
        if target is not None:
            db.add(Relation(
                id=str(uuid.uuid4()),
                from_entry_id=entry.id,
                to_entry_id=target.id,
                kind="backlink",
            ))


async def update_entry(db: AsyncSession, entry_id: str, updates: "EntryUpdate") -> ArticleDetailOut | None:
    result = await db.execute(
        select(Entry).options(selectinload(Entry.tags)).where(Entry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return None

    if updates.title is not None:
        entry.title = updates.title
    if updates.type is not None:
        entry.type = updates.type
    if updates.body is not None:
        entry.body = updates.body
        entry.word_count = len(updates.body.split())
        entry.read_time_min = max(1, round(entry.word_count / 200))
    if updates.excerpt is not None:
        entry.excerpt = updates.excerpt
    if updates.source_url is not None:
        entry.source_url = updates.source_url
    if updates.source_label is not None:
        entry.source_label = updates.source_label
    if updates.is_starred is not None:
        entry.is_starred = updates.is_starred
    if updates.img_url is not None:
        entry.img_url = updates.img_url

    await db.flush()

    if updates.tags is not None:
        await _sync_tags(db, entry, updates.tags)

    await detect_and_store_backlinks(db, entry)
    await db.commit()
    await db.refresh(entry)

    # Fetch current tags after sync
    tag_result = await db.execute(
        select(Tag.name)
        .join(entry_tags, Tag.id == entry_tags.c.tag_id)
        .where(entry_tags.c.entry_id == entry.id)
    )
    tag_names = list(tag_result.scalars().all())

    bl_count = await _backlink_count(db, entry.id)
    return ArticleDetailOut(
        id=entry.id,
        topic_id=entry.topic_id,
        type=entry.type,
        title=entry.title,
        excerpt=entry.excerpt,
        body=entry.body,
        tags=tag_names,
        date=_format_date(entry.created_at),
        source=_entry_source(entry),
        source_url=entry.source_url,
        has_img=entry.has_img,
        img_url=entry.img_url,
        img_height=entry.img_height,
        img_color=entry.img_color,
        is_starred=entry.is_starred,
        word_count=entry.word_count,
        read_time_min=entry.read_time_min,
        backlink_count=bl_count,
    )


async def delete_entry(db: AsyncSession, entry_id: str) -> bool:
    result = await db.execute(select(Entry).where(Entry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return False
    await db.delete(entry)
    await db.commit()
    return True


async def suggest_related(db: AsyncSession, entry_id: str, limit: int = 5) -> list[RelatedEntryOut]:
    """Return entries in the same topic sharing ≥1 tag, sorted by overlap count."""
    # Get this entry's topic and tags
    result = await db.execute(
        select(Entry).options(selectinload(Entry.tags)).where(Entry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return []

    tag_ids_result = await db.execute(
        select(entry_tags.c.tag_id).where(entry_tags.c.entry_id == entry_id)
    )
    tag_ids = [r[0] for r in tag_ids_result]
    if not tag_ids:
        return []

    # Find existing relation targets (both directions)
    existing_result = await db.execute(
        select(Relation.to_entry_id).where(Relation.from_entry_id == entry_id)
    )
    existing_ids = {r[0] for r in existing_result} | {entry_id}

    # Count shared tags per candidate entry
    shared_count = func.count(entry_tags.c.tag_id).label("shared")
    stmt = (
        select(Entry, shared_count)
        .join(entry_tags, Entry.id == entry_tags.c.entry_id)
        .where(
            entry_tags.c.tag_id.in_(tag_ids),
            Entry.topic_id == entry.topic_id,
            Entry.id.notin_(existing_ids),
        )
        .group_by(Entry.id)
        .order_by(shared_count.desc())
        .limit(limit)
    )
    rows = await db.execute(stmt)

    return [
        RelatedEntryOut(id=e.id, relation_id="", title=e.title, type=e.type, img_color=e.img_color)
        for e, _ in rows
    ]
