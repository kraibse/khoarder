from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entry import Entry
from app.models.topic import Topic
from app.models.relation import Relation
from app.schemas.entry import ArticleDetailOut
from app.services.entries import create_entry
from app.services import config as config_svc


async def _require_client(db: AsyncSession):
    base_url = await config_svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    if not base_url.strip():
        raise RuntimeError(
            "LM Studio is not configured. Set LLM_BASE_URL in your .env file "
            "(e.g. LLM_BASE_URL=http://192.168.1.100:1234/v1)."
        )
    from openai import AsyncOpenAI

    timeout = float(await config_svc.get_config_value(db, "llm_timeout", default=str(settings.llm_timeout)))
    return AsyncOpenAI(
        base_url=base_url.rstrip("/") + "/",
        api_key="not-needed",
        timeout=timeout,
    )


async def _chat(db: AsyncSession, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.3) -> str:
    client = await _require_client(db)
    model = await config_svc.get_config_value(db, "llm_model", default=settings.llm_model)
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


async def generate_overview(
    db: AsyncSession,
    topic_id: str,
    entry_ids: list[str] | None = None,
) -> ArticleDetailOut:
    topic_result = await db.execute(select(Topic).where(Topic.id == topic_id))
    topic = topic_result.scalar_one_or_none()
    if topic is None:
        raise ValueError("Topic not found")

    context_entries = int(await config_svc.get_config_value(db, "llm_context_entries", default=str(settings.llm_context_entries)))

    if entry_ids:
        entries_result = await db.execute(
            select(Entry)
            .options(selectinload(Entry.tags))
            .where(Entry.id.in_(entry_ids))
            .order_by(Entry.created_at.desc())
        )
    else:
        entries_result = await db.execute(
            select(Entry)
            .options(selectinload(Entry.tags))
            .where(Entry.topic_id == topic_id)
            .order_by(Entry.is_starred.desc(), Entry.created_at.desc())
            .limit(context_entries)
        )
    entries = list(entries_result.scalars().all())

    if not entries:
        raise ValueError("No entries found for overview generation")

    context_parts: list[str] = []
    for entry in entries:
        snippet = (entry.body or entry.excerpt or "")[:2000]
        context_parts.append(f"[{entry.type}: {entry.title}]\n{snippet}")
    context = "\n\n---\n\n".join(context_parts)

    overview = await _chat(db, [
        {
            "role": "system",
            "content": (
                "You are a knowledge synthesizer. Write a coherent overview article that weaves "
                "together the provided knowledge base entries into a unified narrative. "
                "Use Markdown formatting. Output ONLY the article body. "
                "Do not summarize each entry individually; synthesize them into a flowing whole. "
                "Use [[Title]] to reference related entries where relevant."
            ),
        },
        {
            "role": "user",
            "content": f"Topic: {topic.name}\n\nEntries:\n\n{context}\n\nWrite the overview article:",
        },
    ], max_tokens=2048, temperature=0.4)

    entry = await create_entry(
        db,
        topic_id=topic_id,
        entry_type="Article",
        title=f"Overview: {topic.name}",
        excerpt=overview[:300],
        body=overview,
    )

    return entry


async def suggest_related(
    db: AsyncSession,
    entry_id: str,
) -> list[dict]:
    from app.services.qa import _load_entry
    from app.services.entries import get_entry

    entry = await _load_entry(db, entry_id)
    if entry is None:
        raise ValueError("Entry not found")

    query = f"{entry.title} {entry.excerpt}"[:200]
    from app.services import search as search_svc
    context_entries = int(await config_svc.get_config_value(db, "llm_context_entries", default=str(settings.llm_context_entries)))
    hits = await search_svc.search(db, query, topic_id=entry.topic_id, limit=context_entries + 1)

    existing_result = await db.execute(
        select(Relation.to_entry_id).where(
            Relation.from_entry_id == entry_id,
            Relation.kind == "related",
        )
    )
    existing_ids = {r[0] for r in existing_result} | {entry_id}

    filtered = [h.entry for h in hits if h.entry.id not in existing_ids][:context_entries]
    return [{"id": e.id, "title": e.title, "type": e.type, "img_color": e.img_color} for e in filtered]
