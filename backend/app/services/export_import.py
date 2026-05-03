"""Export a topic to portable JSON; import from the same format."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.topic import Topic
from app.models.entry import Entry
from app.models.tag import Tag, entry_tags
from app.models.attachment import Attachment

EXPORT_FORMAT = "knowledge-hoarder-export"
EXPORT_VERSION = 1


async def export_topic_json(db: AsyncSession, slug_or_id: str) -> dict[str, Any]:
    result = await db.execute(
        select(Topic).where((Topic.slug == slug_or_id) | (Topic.id == slug_or_id))
    )
    topic = result.scalar_one_or_none()
    if topic is None:
        return {}

    entries_result = await db.execute(
        select(Entry)
        .options(selectinload(Entry.tags), selectinload(Entry.attachments))
        .where(Entry.topic_id == topic.id)
        .order_by(Entry.created_at)
    )
    entries = entries_result.scalars().all()

    return {
        "_format": EXPORT_FORMAT,
        "_version": EXPORT_VERSION,
        "_exported_at": datetime.now(timezone.utc).isoformat(),
        "topic": {
            "slug": topic.slug,
            "name": topic.name,
            "color": topic.color,
            "description": topic.description,
        },
        "entries": [
            {
                "id": e.id,
                "type": e.type,
                "title": e.title,
                "excerpt": e.excerpt,
                "body": e.body,
                "tags": [t.name for t in e.tags],
                "source_url": e.source_url,
                "source_label": e.source_label,
                "has_img": e.has_img,
                "img_color": e.img_color,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "attachments": [
                    {
                        "filename": a.filename,
                        "ext": a.ext,
                        "size_bytes": a.size_bytes,
                        "stored_as": a.storage_path,
                    }
                    for a in e.attachments
                ],
            }
            for e in entries
        ],
    }


async def import_topic_json(db: AsyncSession, slug_or_id: str, data: dict[str, Any]) -> dict[str, int]:
    """
    Import entries from an export JSON blob into an existing topic.
    Skips entries where (title, type) already exist in the topic.
    Returns counts of imported and skipped entries.
    """
    import uuid as _uuid

    if data.get("_format") != EXPORT_FORMAT:
        raise ValueError("Unrecognised export format")

    topic_result = await db.execute(
        select(Topic).where((Topic.slug == slug_or_id) | (Topic.id == slug_or_id))
    )
    topic = topic_result.scalar_one_or_none()
    if topic is None:
        raise ValueError("Topic not found")

    existing_result = await db.execute(
        select(Entry.title, Entry.type).where(Entry.topic_id == topic.id)
    )
    existing = {(r.title, r.type) for r in existing_result}

    imported = skipped = 0

    for ed in data.get("entries", []):
        key = (ed.get("title", ""), ed.get("type", "Note"))
        if key in existing:
            skipped += 1
            continue

        entry = Entry(
            id=str(_uuid.uuid4()),
            topic_id=topic.id,
            type=ed.get("type", "Note"),
            title=ed.get("title", "Untitled"),
            excerpt=ed.get("excerpt", ""),
            body=ed.get("body", ""),
            source_url=ed.get("source_url"),
            source_label=ed.get("source_label"),
            has_img=ed.get("has_img", False),
            img_color=ed.get("img_color", "oklch(70% 0.05 200)"),
        )
        db.add(entry)

        for tag_name in ed.get("tags", []):
            tag_result = await db.execute(select(Tag).where(Tag.name == tag_name))
            tag = tag_result.scalar_one_or_none()
            if tag is None:
                tag = Tag(id=str(_uuid.uuid4()), name=tag_name)
                db.add(tag)
                await db.flush()
            await db.execute(insert(entry_tags).values(entry_id=entry.id, tag_id=tag.id))

        imported += 1

    await db.commit()
    return {"imported": imported, "skipped": skipped}
