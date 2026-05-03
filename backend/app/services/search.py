"""
Search abstraction — PostgreSQL FTS implementation (MVP).

To upgrade to OpenSearch:
1. pip install opensearch-py; set OPENSEARCH_URL env var.
2. Implement OpenSearchBackend(SearchBackend):
   - index entries on create/update/delete
   - query via OpenSearch search API → return (entry_id, highlight) pairs
   - load Entry objects from Postgres by ID (same two-phase pattern below)
3. Replace `_backend = PostgresSearchBackend()` with `_backend = OpenSearchBackend()`.
Route handlers and list_entries() need no changes.
"""

from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry


class SearchBackend(ABC):
    @abstractmethod
    async def search(
        self,
        db: AsyncSession,
        query: str,
        topic_id: str | None = None,
        entry_type: str | None = None,
        limit: int = 50,
    ) -> list[tuple[Entry, str | None]]:
        ...


class PostgresSearchBackend(SearchBackend):
    """
    PostgreSQL full-text search.

    Searches title (doubled for natural weight boost), excerpt, body, and
    source_label. Uses websearch_to_tsquery so users can write
    'machine learning' (phrase), -python (exclude), or bare words (AND).

    Returns results ranked by ts_rank_cd with a one-sentence headline from
    the excerpt showing matched terms wrapped in <mark> tags.
    """

    async def search(
        self,
        db: AsyncSession,
        query: str,
        topic_id: str | None = None,
        entry_type: str | None = None,
        limit: int = 50,
    ) -> list[tuple[Entry, str | None]]:
        doc = func.concat_ws(
            " ",
            Entry.title,
            Entry.title,      # repeated → natural weight boost without setweight overhead
            Entry.excerpt,
            Entry.body,
            Entry.source_label,
        )
        tsvec = func.to_tsvector("english", func.coalesce(doc, ""))
        tsq = func.websearch_to_tsquery("english", query)
        rank = func.ts_rank_cd(tsvec, tsq).label("rank")
        headline = func.ts_headline(
            "english",
            func.coalesce(Entry.excerpt, Entry.title),
            tsq,
            "MaxWords=25,MinWords=10,MaxFragments=1,StartSel=<mark>,StopSel=</mark>",
        ).label("headline")

        # Phase 1 — ranked IDs + headlines (lightweight, no joins)
        id_stmt = (
            select(Entry.id, rank, headline)
            .where(tsvec.op("@@")(tsq))
            .order_by(rank.desc())
            .limit(limit)
        )
        if topic_id:
            id_stmt = id_stmt.where(Entry.topic_id == topic_id)
        if entry_type and entry_type.lower() != "all":
            id_stmt = id_stmt.where(Entry.type.ilike(f"{entry_type.rstrip('s')}%"))

        id_rows = await db.execute(id_stmt)
        hits = [(row.id, row.headline) for row in id_rows]
        if not hits:
            return []

        entry_ids = [h[0] for h in hits]
        headline_map: dict[str, str | None] = {h[0]: h[1] for h in hits}

        # Phase 2 — load full Entry objects with tags, preserve rank order
        entry_result = await db.execute(
            select(Entry)
            .options(selectinload(Entry.tags))
            .where(Entry.id.in_(entry_ids))
        )
        entries_by_id = {e.id: e for e in entry_result.scalars().all()}

        return [
            (entries_by_id[eid], headline_map[eid])
            for eid in entry_ids
            if eid in entries_by_id
        ]


_backend: SearchBackend = PostgresSearchBackend()


async def search(
    db: AsyncSession,
    query: str,
    topic_id: str | None = None,
    entry_type: str | None = None,
    limit: int = 50,
) -> list[tuple[Entry, str | None]]:
    return await _backend.search(db, query, topic_id, entry_type, limit)
