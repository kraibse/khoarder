"""Optional LM Studio integrations for the suggest pipeline.

Two surface points:

- `expand_query()` — turn a topic context + optional refine query into 2–3
  diverse search-engine queries. Helps surface heterodox sources the user
  asked for ("discover new and reliable websites").

- `rerank()` — score a candidate batch by relevance to the topic. Returns
  scores in [0,1] keyed by suggestion id. Used as a final pass after the
  fast keyword-overlap rank.

Both functions return safe defaults on failure so the orchestrator can
proceed without the LLM.
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import config as config_svc
from app.services.suggest.base import Suggestion, TopicContext

logger = logging.getLogger(__name__)


async def _client(db: AsyncSession):
    base_url = await config_svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    if not base_url or not base_url.strip():
        return None, None
    timeout = float(await config_svc.get_config_value(db, "llm_timeout", default=str(settings.llm_timeout)))
    model = await config_svc.get_config_value(db, "llm_model", default=settings.llm_model)
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            base_url=base_url.rstrip("/") + "/",
            api_key="not-needed",
            timeout=timeout,
        )
        return client, model
    except Exception as exc:
        logger.warning("llm client init failed: %s", exc)
        return None, None


async def expand_query(db: AsyncSession, ctx: TopicContext) -> list[str]:
    """Generate 2–3 alternate query phrases from topic context.

    The orchestrator will run each expansion through the providers in
    addition to the user's original query, surfacing more diverse sources.
    """
    client, model = await _client(db)
    if client is None:
        return []

    sample = ", ".join(ctx.sample_titles[:5]) or "(none)"
    prompt = (
        "You are a research librarian. Given a knowledge topic and the user's existing entries, "
        "produce 3 short search queries that would surface high-quality, varied sources beyond "
        "what the user already has. Return JSON array of strings. No prose.\n\n"
        f"Topic: {ctx.name}\n"
        f"Description: {ctx.description}\n"
        f"Existing entry titles: {sample}\n"
        f"User refine query: {ctx.refine_query or '(none)'}\n\n"
        'Return JSON like ["query 1", "query 2", "query 3"]'
    )
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=200,
        )
        raw = (resp.choices[0].message.content or "").strip()
        # Tolerate ```json fences
        m = re.search(r"\[[^\[\]]*\]", raw, re.DOTALL)
        if not m:
            return []
        parsed = json.loads(m.group(0))
        if not isinstance(parsed, list):
            return []
        return [str(q).strip() for q in parsed if str(q).strip()][:3]
    except Exception as exc:
        logger.warning("llm query expansion failed: %s", exc)
        return []


async def rerank(
    db: AsyncSession,
    ctx: TopicContext,
    candidates: list[Suggestion],
) -> dict[str, float]:
    """Score candidates against topic context. Returns id→score in [0,1].

    Missing keys mean the LLM didn't score that item — caller should keep
    the existing keyword-based score for those.
    """
    if not candidates:
        return {}
    client, model = await _client(db)
    if client is None:
        return {}

    items = [
        {
            "id": s.id,
            "title": s.title,
            "snippet": (s.excerpt or "")[:240],
            "source": s.source,
        }
        for s in candidates[:24]   # cap prompt size
    ]
    prompt = (
        "You are a relevance scorer. Given a topic and candidate articles, "
        "rate each item from 0.0 (off-topic) to 1.0 (highly relevant) and report only "
        "items you are confident about. Output STRICT JSON of the form "
        '[{"id":"...","score":0.0}, ...]. No prose.\n\n'
        f"Topic: {ctx.name}\n"
        f"Description: {ctx.description}\n"
        f"User refine query: {ctx.refine_query or '(none)'}\n\n"
        f"Candidates:\n{json.dumps(items, ensure_ascii=False)}"
    )
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=600,
        )
        raw = (resp.choices[0].message.content or "").strip()
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if not m:
            return {}
        parsed = json.loads(m.group(0))
        if not isinstance(parsed, list):
            return {}
        out: dict[str, float] = {}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("id", "")).strip()
            try:
                score = float(item.get("score", 0))
            except (TypeError, ValueError):
                continue
            if cid:
                out[cid] = max(0.0, min(1.0, score))
        return out
    except Exception as exc:
        logger.warning("llm rerank failed: %s", exc)
        return {}
