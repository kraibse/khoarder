"""Orchestrator — fan out across providers, dedupe, rank, paginate.

`suggest()` is the only public entry point. It expects a `TopicContext`
(built by the route handler from the topic + sample entries) and returns
a flat ranked list of `Suggestion` objects.
"""
from __future__ import annotations

import asyncio
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.entry import Entry
from app.models.topic import Topic
from app.services import config as config_svc
from app.services.suggest.base import Provider, Suggestion, TopicContext
from app.services.suggest.providers import (
    ArxivProvider,
    HackerNewsProvider,
    OpenAlexProvider,
    SemanticScholarProvider,
    WikipediaProvider,
)
from app.services.suggest.searxng import SearXNGProvider
from app.services.suggest import llm

logger = logging.getLogger(__name__)


# ── Cross-encoder cache ─────────────────────────────────────────────────
_cross_encoder = None


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


# ── Provider registry ───────────────────────────────────────────────────
def _always_on_providers() -> list[Provider]:
    return [
        WikipediaProvider(),
        ArxivProvider(),
        SemanticScholarProvider(),
        OpenAlexProvider(),
        HackerNewsProvider(),
    ]


async def _build_providers(db: AsyncSession) -> list[Provider]:
    providers: list[Provider] = list(_always_on_providers())

    searxng_url = await config_svc.get_config_value(db, "suggest_searxng_url", default=settings.suggest_searxng_url)
    if searxng_url and searxng_url.strip():
        providers.append(SearXNGProvider(searxng_url.strip()))

    return providers


# ── Topic context helpers ───────────────────────────────────────────────
async def build_topic_context(
    db: AsyncSession,
    topic: Topic,
    refine_query: str = "",
    sample_size: int = 8,
) -> TopicContext:
    entries_result = await db.execute(
        select(Entry.title, Entry.excerpt).where(Entry.topic_id == topic.id).limit(sample_size)
    )
    sample_entries = [
        {"title": t, "excerpt": (e or "")[:240]}
        for t, e in entries_result.all() if t
    ]
    sample_titles = [e["title"] for e in sample_entries]

    from app.models.tag import Tag, entry_tags
    tag_result = await db.execute(
        select(Tag.name)
        .join(entry_tags, Tag.id == entry_tags.c.tag_id)
        .join(Entry, Entry.id == entry_tags.c.entry_id)
        .where(Entry.topic_id == topic.id)
        .group_by(Tag.name)
        .order_by(func.count().desc())
        .limit(12)
    )
    sample_tags = [r for r in tag_result.scalars().all() if r]

    return TopicContext(
        name=topic.name,
        description=topic.description or "",
        sample_titles=sample_titles,
        sample_tags=sample_tags,
        refine_query=refine_query.strip(),
        sample_entries=sample_entries,
    )


def _build_query_set(ctx: TopicContext, expansions: list[str]) -> list[str]:
    base = (ctx.refine_query or ctx.name).strip()
    queries: list[str] = []
    if base:
        queries.append(base)
    if not ctx.refine_query and ctx.description:
        queries.append(f"{ctx.name} {ctx.description}".strip())
    queries.extend(expansions)
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        norm = re.sub(r"\s+", " ", q.strip().lower())
        if norm and norm not in seen:
            seen.add(norm)
            out.append(q.strip())
    return out[:4]   # cap fan-out width


# ── Ranking ─────────────────────────────────────────────────────────────
def _keyword_overlap(text: str, keywords: list[str]) -> float:
    if not keywords or not text:
        return 0.0
    text_l = text.lower()
    hits = sum(1 for k in keywords if k in text_l)
    return min(1.0, hits / max(3, len(keywords)))


def _score(s: Suggestion, ctx: TopicContext, weight_map: dict[str, float]) -> float:
    keywords = ctx.keywords()
    text = f"{s.title}\n{s.excerpt}\n{' '.join(s.tags)}".lower()
    overlap = _keyword_overlap(text, keywords)
    src_weight = weight_map.get(s.provider, 1.0)
    base = max(s.relevance, 0.4)   # provider's own hint

    # Topic-mismatch penalty: if result contains NONE of the core topic words, slash score
    core_topic_words = [w for w in ctx.name.lower().split() if len(w) > 2]
    core_topic_words += [w for w in (ctx.refine_query or "").lower().split() if len(w) > 2]
    has_core = any(w in text for w in core_topic_words)
    mismatch_penalty = 0.55 if has_core else 0.15

    # Boost for matching existing entry titles (strong signal of relevance)
    title_boost = 0.0
    for entry_title in ctx.sample_titles:
        entry_words = [w.strip(",.!?;:\"'()[]") for w in entry_title.lower().split() if len(w.strip(",.!?;:\"'()[]")) > 2]
        if entry_words and all(w in text for w in entry_words[:3]):  # match first 3 significant words
            title_boost = 0.15
            break
        # Partial match: at least 2 words from any entry title
        matches = sum(1 for w in entry_words if w in text)
        if len(entry_words) >= 2 and matches >= 2:
            title_boost = max(title_boost, 0.08)

    return min(1.0, base * 0.35 + overlap * 0.5 * src_weight * mismatch_penalty + title_boost + 0.05)


def _dedupe(suggestions: list[Suggestion]) -> list[Suggestion]:
    seen: set[str] = set()
    out: list[Suggestion] = []
    for s in suggestions:
        key = (s.source_url or s.id).split("?")[0].rstrip("/")
        if key and key not in seen:
            seen.add(key)
            out.append(s)
    return out


# ── Public entry point ──────────────────────────────────────────────────
async def suggest(
    db: AsyncSession,
    topic: Topic,
    refine_query: str = "",
    offset: int = 0,
    limit: int = 5,
) -> list[Suggestion]:
    ctx = await build_topic_context(db, topic, refine_query=refine_query)
    providers = await _build_providers(db)
    weight_map = {p.name: p.weight for p in providers}

    use_expand = (await config_svc.get_config_value(
        db, "suggest_use_llm_expand", default=str(settings.suggest_use_llm_expand).lower()
    )).lower() in ("true", "1", "yes")
    use_rerank = (await config_svc.get_config_value(
        db, "suggest_use_llm_rerank", default=str(settings.suggest_use_llm_rerank).lower()
    )).lower() in ("true", "1", "yes")

    expansions: list[str] = []
    if use_expand:
        expansions = await llm.expand_query(db, ctx)

    queries = _build_query_set(ctx, expansions)
    if not queries:
        return []

    # Fan out: each provider × each query → flatten
    per_provider_per_query = max(4, (limit + offset) // max(1, len(providers)) + 2)
    tasks = []
    for p in providers:
        for q in queries:
            tasks.append(p.fetch(q, limit=per_provider_per_query))
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    flat: list[Suggestion] = []
    for r in raw_results:
        if isinstance(r, Exception):
            logger.warning("provider error: %s", r)
            continue
        flat.extend(r)

    # Drop suggestions whose canonical URL is already an entry in this topic.
    if flat:
        url_result = await db.execute(
            select(Entry.source_url).where(Entry.topic_id == topic.id, Entry.source_url.isnot(None))
        )
        existing_urls = {(u or "").rstrip("/") for u in url_result.scalars().all() if u}
        if existing_urls:
            flat = [s for s in flat if (s.source_url or "").rstrip("/") not in existing_urls]

    deduped = _dedupe(flat)
    for s in deduped:
        s.relevance = _score(s, ctx, weight_map)
    deduped.sort(key=lambda s: s.relevance, reverse=True)

    # Cross-encoder rerank on top-N
    if len(deduped) > 3:
        try:
            ce = _get_cross_encoder()
            top_n = deduped[: max(20, offset + limit + 5)]
            # Build focused query from high-signal terms only
            core_terms = [ctx.name]
            if ctx.refine_query:
                core_terms.append(ctx.refine_query)
            # Add key description words (skip stop words)
            desc_words = [
                w.strip(",.!?;:\"'()[]")
                for w in (ctx.description or "").lower().split()
                if len(w.strip(",.!?;:\"'()[]")) > 3
                and w.strip(",.!?;:\"'()[]") not in {
                    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
                    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
                    "been", "being", "have", "has", "had", "will", "would", "could",
                    "should", "may", "might", "must", "can", "shall", "this", "that",
                    "these", "those", "all", "any", "both", "each", "few", "more",
                    "most", "other", "some", "such", "no", "nor", "not", "only",
                    "own", "same", "so", "than", "too", "very", "just", "now", "then",
                    "also", "about", "into", "through", "during", "before", "after",
                    "above", "below", "up", "down", "out", "off", "over", "under",
                    "again", "further", "once", "here", "there", "type", "types",
                    "currently", "recently", "earth",
                }
            ]
            core_terms.extend(desc_words[:5])  # top 5 description words
            core_terms.extend(ctx.sample_titles[:3])
            query = " ".join(core_terms).strip()
            pairs = [
                [query, f"{s.title}\n{s.excerpt}"]
                for s in top_n
            ]
            ce_scores = ce.predict(pairs)
            for i, s in enumerate(top_n):
                raw = float(ce_scores[i])
                # cross-encoder returns raw logits — sigmoid to [0,1]
                norm = 1.0 / (1.0 + (2.718281828459045 ** -raw))
                s.relevance = 0.45 * s.relevance + 0.55 * norm
            top_n.sort(key=lambda s: s.relevance, reverse=True)
            deduped[: len(top_n)] = top_n
        except Exception as exc:
            logger.warning("cross-encoder rerank failed: %s", exc)

    # Optional LLM rerank on top-N
    if use_rerank and deduped:
        top_n = deduped[: max(20, offset + limit + 5)]
        scores = await llm.rerank(db, ctx, top_n)
        if scores:
            for s in top_n:
                if s.id in scores:
                    s.relevance = max(s.relevance, scores[s.id])
            deduped.sort(key=lambda s: s.relevance, reverse=True)

    # Normalize to [0.1, 1.0] so top result shows ~95% and bottom ~10%
    if deduped:
        vals = [s.relevance for s in deduped]
        lo, hi = min(vals), max(vals)
        if hi > lo:
            for s in deduped:
                s.relevance = 0.1 + 0.9 * (s.relevance - lo) / (hi - lo)
        else:
            for s in deduped:
                s.relevance = 0.5

    return deduped[offset : offset + limit]
