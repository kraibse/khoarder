import re
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.topic import Topic
from app.schemas.topic import TopicOut, TopicCreate, TopicUpdate


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "topic"


async def list_topics(db: AsyncSession) -> list[TopicOut]:
    result = await db.execute(select(Topic).order_by(Topic.name))
    topics = result.scalars().all()

    out = []
    for t in topics:
        count_result = await db.execute(
            select(func.count()).where(Entry.topic_id == t.id)
        )
        count = count_result.scalar_one()
        out.append(TopicOut(
            id=t.id,
            slug=t.slug,
            name=t.name,
            color=t.color,
            description=t.description,
            count=count,
        ))
    return out


async def get_topic(db: AsyncSession, slug_or_id: str) -> TopicOut | None:
    result = await db.execute(
        select(Topic).where((Topic.slug == slug_or_id) | (Topic.id == slug_or_id))
    )
    t = result.scalar_one_or_none()
    if t is None:
        return None

    count_result = await db.execute(select(func.count()).where(Entry.topic_id == t.id))
    count = count_result.scalar_one()
    return TopicOut(id=t.id, slug=t.slug, name=t.name, color=t.color, description=t.description, count=count)


async def get_topic_tags(db: AsyncSession, slug_or_id: str) -> list[str]:
    from sqlalchemy import distinct
    from app.models.tag import Tag, entry_tags

    result = await db.execute(
        select(Topic).where((Topic.slug == slug_or_id) | (Topic.id == slug_or_id))
    )
    t = result.scalar_one_or_none()
    if t is None:
        return []

    tag_result = await db.execute(
        select(distinct(Tag.name))
        .join(entry_tags, Tag.id == entry_tags.c.tag_id)
        .join(Entry, Entry.id == entry_tags.c.entry_id)
        .where(Entry.topic_id == t.id)
        .order_by(Tag.name)
    )
    return list(tag_result.scalars().all())


async def _unique_slug(db: AsyncSession, base: str) -> str:
    """Return base slug, appending -2, -3 … if already taken."""
    candidate = base
    n = 2
    while True:
        result = await db.execute(select(Topic).where(Topic.slug == candidate))
        if result.scalar_one_or_none() is None:
            return candidate
        candidate = f"{base}-{n}"
        n += 1


async def create_topic(db: AsyncSession, data: TopicCreate) -> TopicOut:
    slug = await _unique_slug(db, _slugify(data.name))
    topic = Topic(
        id=str(uuid.uuid4()),
        slug=slug,
        name=data.name,
        color=data.color,
        description=data.description,
    )
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return TopicOut(id=topic.id, slug=topic.slug, name=topic.name,
                    color=topic.color, description=topic.description, count=0)


async def update_topic(db: AsyncSession, slug_or_id: str, data: TopicUpdate) -> TopicOut | None:
    result = await db.execute(
        select(Topic).where((Topic.slug == slug_or_id) | (Topic.id == slug_or_id))
    )
    topic = result.scalar_one_or_none()
    if topic is None:
        return None

    if data.name is not None:
        topic.name = data.name
        topic.slug = await _unique_slug(db, _slugify(data.name))
    if data.description is not None:
        topic.description = data.description
    if data.color is not None:
        topic.color = data.color

    await db.commit()
    await db.refresh(topic)

    count_result = await db.execute(select(func.count()).where(Entry.topic_id == topic.id))
    count = count_result.scalar_one()
    return TopicOut(id=topic.id, slug=topic.slug, name=topic.name,
                    color=topic.color, description=topic.description, count=count)
