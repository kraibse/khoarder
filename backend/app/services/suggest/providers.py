"""Built-in discovery providers — all free, no auth required.

Each provider is best-effort: network errors are logged and swallowed so a
single bad source can't break the orchestrator's parallel fan-out.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import httpx

from app.services.suggest.base import Provider, Suggestion

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 12
_BROWSER_HEADERS = {
    "User-Agent": (
        "knowledge-hoarder/1.0 (+https://github.com/) "
        "Mozilla/5.0 (compatible; suggestion-fetcher)"
    ),
    "Accept": "application/json,application/xml,text/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _short(text: str, n: int = 280) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


# ── Wikipedia ──────────────────────────────────────────────────────────
class WikipediaProvider(Provider):
    name = "wikipedia"
    weight = 0.85

    async def fetch(self, query: str, limit: int = 10) -> list[Suggestion]:
        if not query.strip():
            return []
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": str(limit),
            "srprop": "snippet|titlesnippet",
            "format": "json",
            "origin": "*",
        }
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, headers=_BROWSER_HEADERS) as c:
                resp = await c.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("wikipedia search failed: %s", exc)
            return []

        out: list[Suggestion] = []
        for hit in data.get("query", {}).get("search", []):
            title = hit.get("title", "")
            if not title:
                continue
            snippet = re.sub(r"<[^>]+>", "", hit.get("snippet", ""))
            page_url = f"https://en.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}"
            out.append(Suggestion(
                id=f"wikipedia:{hit.get('pageid', title)}",
                title=title,
                excerpt=_short(snippet),
                source=f"Wikipedia",
                source_url=page_url,
                type="Reference",
                relevance=0.5,
                tags=[],
                provider=self.name,
            ))
        return out


# ── arXiv ──────────────────────────────────────────────────────────────
class ArxivProvider(Provider):
    name = "arxiv"
    weight = 1.05

    async def fetch(self, query: str, limit: int = 10) -> list[Suggestion]:
        if not query.strip():
            return []
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "max_results": str(limit),
            "sortBy": "relevance",
        }
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, headers=_BROWSER_HEADERS) as c:
                resp = await c.get(url, params=params)
                resp.raise_for_status()
                xml_text = resp.text
        except Exception as exc:
            logger.warning("arxiv search failed: %s", exc)
            return []

        ns = {"a": "http://www.w3.org/2005/Atom"}
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.warning("arxiv parse failed: %s", exc)
            return []

        out: list[Suggestion] = []
        for entry in root.findall("a:entry", ns):
            title_el = entry.find("a:title", ns)
            link_el = entry.find("a:id", ns)
            summary_el = entry.find("a:summary", ns)
            if title_el is None or link_el is None:
                continue
            title = (title_el.text or "").strip()
            link = (link_el.text or "").strip()
            authors = [a.findtext("a:name", default="", namespaces=ns) for a in entry.findall("a:author", ns)]
            author_label = authors[0] if authors else "arXiv"
            if len(authors) > 1:
                author_label += " et al."
            published = (entry.findtext("a:published", default="", namespaces=ns) or "")[:4]
            source = f"arXiv · {author_label}{', ' + published if published else ''}"
            out.append(Suggestion(
                id=f"arxiv:{link.rsplit('/', 1)[-1]}",
                title=title,
                excerpt=_short(summary_el.text if summary_el is not None else ""),
                source=source,
                source_url=link,
                type="Paper",
                relevance=0.55,
                tags=[],
                provider=self.name,
            ))
        return out


# ── Semantic Scholar ───────────────────────────────────────────────────
class SemanticScholarProvider(Provider):
    name = "semantic_scholar"
    weight = 1.10

    async def fetch(self, query: str, limit: int = 10) -> list[Suggestion]:
        if not query.strip():
            return []
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": str(limit),
            "fields": "title,abstract,authors.name,year,url,externalIds",
        }
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, headers=_BROWSER_HEADERS) as c:
                resp = await c.get(url, params=params)
                if resp.status_code in (429, 403):
                    logger.info("semantic_scholar rate-limited (%s)", resp.status_code)
                    return []
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("semantic_scholar search failed: %s", exc)
            return []

        out: list[Suggestion] = []
        for paper in data.get("data", []):
            title = paper.get("title")
            if not title:
                continue
            authors = [a.get("name", "") for a in (paper.get("authors") or [])]
            author_label = authors[0] if authors else "Unknown"
            if len(authors) > 1:
                author_label += " et al."
            year = paper.get("year")
            paper_id = paper.get("externalIds", {}).get("DOI") or paper.get("externalIds", {}).get("ArXiv") or paper.get("title")
            out.append(Suggestion(
                id=f"semanticscholar:{paper_id}",
                title=title,
                excerpt=_short(paper.get("abstract") or ""),
                source=f"Semantic Scholar · {author_label}{', ' + str(year) if year else ''}",
                source_url=paper.get("url") or "",
                type="Paper",
                relevance=0.6,
                tags=[],
                provider=self.name,
            ))
        return [s for s in out if s.source_url]


# ── OpenAlex ───────────────────────────────────────────────────────────
class OpenAlexProvider(Provider):
    name = "openalex"
    weight = 1.0

    async def fetch(self, query: str, limit: int = 10) -> list[Suggestion]:
        if not query.strip():
            return []
        url = "https://api.openalex.org/works"
        params = {
            "search": query,
            "per-page": str(limit),
            "select": "id,title,abstract_inverted_index,authorships,publication_year,primary_location,doi",
        }
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, headers=_BROWSER_HEADERS) as c:
                resp = await c.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("openalex search failed: %s", exc)
            return []

        out: list[Suggestion] = []
        for work in data.get("results", []):
            title = work.get("title")
            if not title:
                continue
            abstract = _reconstruct_inverted_abstract(work.get("abstract_inverted_index"))
            authorships = work.get("authorships") or []
            authors = [a.get("author", {}).get("display_name", "") for a in authorships if a.get("author")]
            author_label = authors[0] if authors else "Unknown"
            if len(authors) > 1:
                author_label += " et al."
            year = work.get("publication_year")
            primary = work.get("primary_location") or {}
            page_url = primary.get("landing_page_url") or work.get("doi") or work.get("id")
            out.append(Suggestion(
                id=f"openalex:{work.get('id')}",
                title=title,
                excerpt=_short(abstract),
                source=f"OpenAlex · {author_label}{', ' + str(year) if year else ''}",
                source_url=page_url or "",
                type="Paper",
                relevance=0.55,
                tags=[],
                provider=self.name,
            ))
        return [s for s in out if s.source_url]


def _reconstruct_inverted_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos: dict[int, str] = {}
    for word, positions in inv.items():
        for p in positions or []:
            pos[p] = word
    return " ".join(pos[k] for k in sorted(pos))


# ── Hacker News (Algolia) ──────────────────────────────────────────────
class HackerNewsProvider(Provider):
    name = "hackernews"
    weight = 0.65

    async def fetch(self, query: str, limit: int = 10) -> list[Suggestion]:
        if not query.strip():
            return []
        url = "https://hn.algolia.com/api/v1/search"
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": str(limit),
        }
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, headers=_BROWSER_HEADERS) as c:
                resp = await c.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("hackernews search failed: %s", exc)
            return []

        out: list[Suggestion] = []
        for hit in data.get("hits", []):
            title = hit.get("title")
            link = hit.get("url")
            if not title or not link:
                continue
            out.append(Suggestion(
                id=f"hackernews:{hit.get('objectID')}",
                title=title,
                excerpt=_short(hit.get("story_text") or hit.get("comment_text") or ""),
                source=f"Hacker News · {hit.get('points', 0)}↑",
                source_url=link,
                type="Article",
                relevance=0.45,
                tags=[],
                provider=self.name,
            ))
        return out
