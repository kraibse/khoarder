"""
Search abstraction — PostgreSQL FTS implementation (MVP).

To upgrade to OpenSearch:
1. pip install opensearch-py; set OPENSEARCH_URL env var.
2. Implement OpenSearchBackend(SearchBackend):
   - index entries on create/update/delete
   - query via OpenSearch search API → return SearchHit list
   - load Entry objects from Postgres by ID (same two-phase pattern below)
3. Replace `_backend = PostgresSearchBackend()` with `_backend = OpenSearchBackend()`.
Route handlers and list_entries() need no changes.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from sqlalchemy import Integer, func, literal, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry


HEADLINE_DELIM = ""  # ASCII unit separator — won't appear in user content
MAX_FRAGMENTS = 12
MATCH_COUNT_CAP = 250


@dataclass
class SearchHit:
    entry: Entry
    headline: str | None = None         # first fragment (back-compat)
    headlines: list[str] = field(default_factory=list)  # up to MAX_FRAGMENTS
    match_count: int = 0                # approx total occurrences in body+excerpt+title


class SearchBackend(ABC):
    @abstractmethod
    async def search(
        self,
        db: AsyncSession,
        query: str,
        topic_id: str | None = None,
        entry_type: str | None = None,
        limit: int = 50,
    ) -> list[SearchHit]:
        ...


def _build_terms_pattern(query: str) -> str | None:
    """Build a PG regex alternation of positive query terms, escaped, w/ word boundaries."""
    terms = [t for t in query.split() if t and not t.startswith("-")]
    cleaned = [re.escape(t) for t in terms if t]
    if not cleaned:
        return None
    return r"\m(?:" + "|".join(cleaned) + r")\M"


class PostgresSearchBackend(SearchBackend):
    """
    PostgreSQL full-text search.

    Searches title (doubled for natural weight boost), excerpt, body, and
    source_label. Uses websearch_to_tsquery so users can write
    'machine learning' (phrase), -python (exclude), or bare words (AND).

    Returns SearchHit rows ranked by ts_rank_cd. Each hit carries up to
    MAX_FRAGMENTS headline fragments (delimiter-joined string from PG,
    split client-side here) plus a count of total matches across the
    body+excerpt+title document, capped for safety.
    """

    async def search(
        self,
        db: AsyncSession,
        query: str,
        topic_id: str | None = None,
        entry_type: str | None = None,
        limit: int = 50,
    ) -> list[SearchHit]:
        doc = func.concat_ws(
            " ",
            Entry.title,
            Entry.title,      # repeated → natural weight boost without setweight overhead
            Entry.excerpt,
            Entry.body,
            Entry.source_label,
        )
        # Snippet doc — body first so headlines come from full content, not just excerpt.
        snippet_doc = func.concat_ws(
            "\n\n",
            func.coalesce(Entry.body, ""),
            func.coalesce(Entry.excerpt, ""),
            func.coalesce(Entry.title, ""),
        )
        tsvec = func.to_tsvector("english", func.coalesce(doc, ""))
        tsq = func.websearch_to_tsquery("english", query)
        rank = func.ts_rank_cd(tsvec, tsq).label("rank")
        headlines = func.ts_headline(
            "english",
            snippet_doc,
            tsq,
            (
                f"MaxWords=20,MinWords=6,MaxFragments={MAX_FRAGMENTS},"
                f"FragmentDelimiter={HEADLINE_DELIM},"
                "StartSel=<mark>,StopSel=</mark>"
            ),
        ).label("headlines")

        terms_pattern = _build_terms_pattern(query)
        if terms_pattern:
            match_count_expr = func.least(
                func.coalesce(
                    func.regexp_count(snippet_doc, terms_pattern, 1, "i"), 0
                ),
                MATCH_COUNT_CAP,
            )
        else:
            match_count_expr = literal(0, type_=Integer)
        match_count = match_count_expr.label("match_count")

        # Phase 1 — ranked IDs + headlines + counts (lightweight, no joins)
        id_stmt = (
            select(Entry.id, rank, headlines, match_count)
            .where(tsvec.op("@@")(tsq))
            .order_by(rank.desc())
            .limit(limit)
        )
        if topic_id:
            id_stmt = id_stmt.where(Entry.topic_id == topic_id)
        if entry_type and entry_type.lower() != "all":
            id_stmt = id_stmt.where(Entry.type.ilike(f"{entry_type.rstrip('s')}%"))

        id_rows = await db.execute(id_stmt)
        meta = [(row.id, row.headlines, int(row.match_count or 0)) for row in id_rows]
        if not meta:
            return []

        entry_ids = [m[0] for m in meta]
        meta_map: dict[str, tuple[str | None, int]] = {m[0]: (m[1], m[2]) for m in meta}

        # Phase 2 — load full Entry objects with tags, preserve rank order
        entry_result = await db.execute(
            select(Entry)
            .options(selectinload(Entry.tags))
            .where(Entry.id.in_(entry_ids))
        )
        entries_by_id = {e.id: e for e in entry_result.scalars().all()}

        out: list[SearchHit] = []
        for eid in entry_ids:
            if eid not in entries_by_id:
                continue
            raw_headline, count = meta_map[eid]
            fragments = _split_headlines(raw_headline)
            out.append(SearchHit(
                entry=entries_by_id[eid],
                headline=fragments[0] if fragments else None,
                headlines=fragments,
                match_count=max(count, len(fragments)),
            ))
        return out


def _split_headlines(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(HEADLINE_DELIM)]
    return [p for p in parts if p]


_backend: SearchBackend = PostgresSearchBackend()


async def search(
    db: AsyncSession,
    query: str,
    topic_id: str | None = None,
    entry_type: str | None = None,
    limit: int = 50,
) -> list[SearchHit]:
    return await _backend.search(db, query, topic_id=topic_id, entry_type=entry_type, limit=limit)
