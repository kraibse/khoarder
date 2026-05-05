"""Optional SearXNG provider — only active when settings.suggest_searxng_url is set.

SearXNG returns JSON via /search?format=json. The base URL is user-configured in
Settings; we trust the user not to point it at a hostile instance, but we still
swallow errors and timeouts to keep the rest of the orchestrator alive.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from app.services.suggest.base import Provider, Suggestion

logger = logging.getLogger(__name__)

_TIMEOUT = 15
_HEADERS = {
    "User-Agent": "knowledge-hoarder/1.0 (+searxng-discovery)",
    "Accept": "application/json",
}


class SearXNGProvider(Provider):
    name = "searxng"
    weight = 0.95

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def fetch(self, query: str, limit: int = 10) -> list[Suggestion]:
        if not self.base_url or not query.strip():
            return []
        url = f"{self.base_url}/search"
        params = {
            "q": query,
            "format": "json",
            "categories": "general,science",
            "safesearch": "1",
        }
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as c:
                resp = await c.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("searxng search failed (%s): %s", self.base_url, exc)
            return []

        out: list[Suggestion] = []
        for hit in data.get("results", [])[:limit]:
            link = hit.get("url") or ""
            title = hit.get("title") or ""
            if not link or not title:
                continue
            host = urlparse(link).netloc or "web"
            out.append(Suggestion(
                id=f"searxng:{link}",
                title=title,
                excerpt=hit.get("content", "") or "",
                source=f"{host}",
                source_url=link,
                type="Article",
                relevance=0.5,
                tags=hit.get("tags") or [],
                provider=self.name,
            ))
        return out
