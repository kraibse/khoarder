"""Cheapest fetch tier: a plain async HTTP request."""
from __future__ import annotations

import logging
import time

import httpx

from app.services.imports.challenges import classify_html
from app.services.imports.fast_paths import is_wikipedia
from app.services.imports.strategies.base import FetchStrategy
from app.services.imports.types import AcquireResult, ChallengeType, ImportRequest

logger = logging.getLogger(__name__)


_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}


class StaticHTTPStrategy(FetchStrategy):
    name = "static_http"

    def is_available(self, req: ImportRequest) -> bool:
        return True

    async def fetch(self, req: ImportRequest) -> AcquireResult:
        start = time.monotonic()
        exempt = is_wikipedia(req.url)
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=req.static_fetch_timeout,
            ) as client:
                resp = await client.get(req.url, headers=_BROWSER_HEADERS)
            elapsed = int((time.monotonic() - start) * 1000)
            html = resp.text
            challenge = classify_html(html, status_code=resp.status_code, exempt=exempt)
            if resp.is_error and challenge == ChallengeType.NONE:
                challenge = ChallengeType.HARD_BLOCK
            return AcquireResult(
                html=html if challenge in (ChallengeType.NONE, ChallengeType.SOFT_JS, ChallengeType.EMPTY_SHELL) else "",
                final_url=str(resp.url),
                strategy=self.name,
                challenge=challenge,
                status_code=resp.status_code,
                duration_ms=elapsed,
            )
        except httpx.TimeoutException:
            return AcquireResult(
                html="", final_url=req.url, strategy=self.name,
                challenge=ChallengeType.HARD_BLOCK, status_code=None,
                duration_ms=int((time.monotonic() - start) * 1000),
                note="static fetch timed out",
            )
        except Exception as exc:
            logger.debug("static fetch failed for %s: %s", req.url, exc)
            return AcquireResult(
                html="", final_url=req.url, strategy=self.name,
                challenge=ChallengeType.HARD_BLOCK, status_code=None,
                duration_ms=int((time.monotonic() - start) * 1000),
                note=str(exc),
            )
