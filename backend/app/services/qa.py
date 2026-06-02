"""
LM Studio Q&A and article-assistance service.

All functions are user-triggered. Nothing is called automatically.
LM Studio is accessed via the OpenAI-compatible API (openai SDK, base_url override).
"""

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entry import Entry
from app.schemas.qa import (
    AssistExtendResponse,
    AssistRelatedEntry,
    AssistRelatedResponse,
    AssistSummarizeResponse,
    AssistTagsResponse,
    QAResponse,
    QASource,
)
from app.services import config as config_svc


# ── LM Studio client ──────────────────────────────────────────────────────────

async def _require_client(db: AsyncSession):
    """Return an AsyncOpenAI client pointed at LM Studio. Raises if not configured."""
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
        api_key="not-needed",           # LM Studio ignores the key
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


# ── Retrieval helpers ─────────────────────────────────────────────────────────

async def _retrieve(db: AsyncSession, topic_id: str, query: str, limit: int) -> list[Entry]:
    """FTS retrieval for the topic; falls back to most-recent if no hits."""
    from app.services import search as search_svc

    hits = await search_svc.search(db, query, topic_id=topic_id, limit=limit)
    if hits:
        return [hit.entry for hit in hits]

    # Fallback: most recent entries
    result = await db.execute(
        select(Entry)
        .options(selectinload(Entry.tags))
        .where(Entry.topic_id == topic_id)
        .order_by(Entry.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def _load_entry(db: AsyncSession, entry_id: str) -> Entry | None:
    result = await db.execute(
        select(Entry)
        .options(selectinload(Entry.tags))
        .where(Entry.id == entry_id)
    )
    return result.scalar_one_or_none()


# ── Q&A ───────────────────────────────────────────────────────────────────────

async def ask_question(db: AsyncSession, question: str, topic_id: str) -> QAResponse:
    context_entries = int(await config_svc.get_config_value(db, "llm_context_entries", default=str(settings.llm_context_entries)))
    entries = await _retrieve(db, topic_id, question, context_entries)

    context_parts: list[str] = []
    sources: list[QASource] = []
    for entry in entries:
        body_snippet = (entry.body or entry.excerpt or "")[:2000]
        context_parts.append(f"[{entry.type}: {entry.title}]\n{body_snippet}")
        sources.append(QASource(
            id=entry.id,
            title=entry.title,
            type=entry.type,
            snippet=(entry.excerpt or (entry.body or "")[:200] or "").strip(),
        ))

    context = "\n\n---\n\n".join(context_parts)

    answer = await _chat(db, [
        {
            "role": "system",
            "content": (
                "You are a knowledge assistant. Answer the question based ONLY on the provided "
                "knowledge base entries. If the answer is not in the provided entries, say so. "
                "Be concise. Cite entry titles when you reference them."
            ),
        },
        {
            "role": "user",
            "content": f"Knowledge base entries:\n\n{context}\n\n---\n\nQuestion: {question}",
        },
    ], max_tokens=1024)

    return QAResponse(answer=answer, sources=sources)


# ── Article assistance ────────────────────────────────────────────────────────

async def assist_summarize(db: AsyncSession, entry_id: str) -> AssistSummarizeResponse:
    entry = await _load_entry(db, entry_id)
    if entry is None:
        raise ValueError("Entry not found")

    body = (entry.body or entry.excerpt or "").strip()
    if not body:
        return AssistSummarizeResponse(summary="No content to summarize.")

    summary = await _chat(db, [
        {
            "role": "system",
            "content": "Summarize the following article in 2-3 sentences. Output only the summary, no preamble.",
        },
        {
            "role": "user",
            "content": f"Title: {entry.title}\n\n{body[:4000]}",
        },
    ], max_tokens=256)

    return AssistSummarizeResponse(summary=summary)


async def assist_tags(db: AsyncSession, entry_id: str) -> AssistTagsResponse:
    entry = await _load_entry(db, entry_id)
    if entry is None:
        raise ValueError("Entry not found")

    existing = {t.name for t in entry.tags}
    body = ((entry.excerpt or "") + "\n" + (entry.body or "")).strip()

    raw = await _chat(db, [
        {
            "role": "system",
            "content": (
                "Suggest 3-5 relevant tags for this article. "
                "Output ONLY a comma-separated list of lowercase tags. "
                "No explanations, no numbering, no markdown."
            ),
        },
        {
            "role": "user",
            "content": f"Title: {entry.title}\n\n{body[:2000]}",
        },
    ], max_tokens=64, temperature=0.2)

    tags = [t.strip().lower() for t in raw.replace("\n", ",").split(",") if t.strip()]
    # Filter out already-applied tags, cap at 6
    new_tags = [t for t in tags if t not in existing][:6]
    return AssistTagsResponse(tags=new_tags)


async def assist_related(db: AsyncSession, entry_id: str) -> AssistRelatedResponse:
    entry = await _load_entry(db, entry_id)
    if entry is None:
        raise ValueError("Entry not found")

    # Use the entry's title + excerpt as the search query
    query = f"{entry.title} {entry.excerpt}"[:200]
    context_entries = int(await config_svc.get_config_value(db, "llm_context_entries", default=str(settings.llm_context_entries)))
    candidates = await _retrieve(db, entry.topic_id, query, context_entries + 1)

    # Exclude the entry itself and already-related entries
    from app.models.relation import Relation
    existing_result = await db.execute(
        select(Relation.to_entry_id).where(
            Relation.from_entry_id == entry_id,
            Relation.kind == "related",
        )
    )
    existing_ids = {r[0] for r in existing_result} | {entry_id}

    filtered = [e for e in candidates if e.id not in existing_ids][:context_entries]

    return AssistRelatedResponse(entries=[
        AssistRelatedEntry(id=e.id, title=e.title, type=e.type, img_color=e.img_color)
        for e in filtered
    ])


async def assist_extend(db: AsyncSession, entry_id: str, prompt: str = "") -> AssistExtendResponse:
    entry = await _load_entry(db, entry_id)
    if entry is None:
        raise ValueError("Entry not found")

    body = (entry.body or "").strip()
    direction = f"Direction: {prompt.strip()}\n\n" if prompt.strip() else ""

    default_prompt = (
        "You are a knowledge-base writing assistant. Write a thoughtful extension for "
        "the given article. Output ONLY the extension text in Markdown, ready to append "
        "after existing content. Do not repeat, summarize, or reference the existing text."
    )
    system_prompt = await config_svc.get_config_value(db, "system_prompt", default=settings.system_prompt or default_prompt)
    system_prompt = system_prompt.strip() or default_prompt

    extension = await _chat(db, [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": (
                f"Title: {entry.title}\n\n"
                f"Existing content:\n{body[:3000]}\n\n"
                f"{direction}"
                "Write the extension:"
            ),
        },
    ], max_tokens=1024, temperature=0.6)

    return AssistExtendResponse(extension=extension)
