"""Browserless.io remote browser fetch.

Uses the `/content` endpoint which renders a page server-side and returns
the resulting HTML directly. Token + base URL come from runtime config so
nothing is hardcoded.
"""
from __future__ import annotations

import logging
import time

import httpx

from app.services.imports.challenges import classify_html
from app.services.imports.fast_paths import is_wikipedia
from app.services.imports.strategies.base import FetchStrategy
from app.services.imports.types import AcquireResult, ChallengeType, ImportRequest

logger = logging.getLogger(__name__)


class BrowserlessStrategy(FetchStrategy):
    name = "browserless"

    def is_available(self, req: ImportRequest) -> bool:
        return (
            req.browserless_enabled
            and bool(req.browserless_token.strip())
            and bool(req.browserless_url.strip())
        )

    async def fetch(self, req: ImportRequest) -> AcquireResult:
        start = time.monotonic()
        exempt = is_wikipedia(req.url)
        endpoint = req.browserless_url.rstrip("/") + "/content"
        payload = {
            "url": req.url,
            "gotoOptions": {"waitUntil": "networkidle2", "timeout": req.browserless_timeout * 1000},
        }
        params = {"token": req.browserless_token}
        try:
            async with httpx.AsyncClient(timeout=req.browserless_timeout + 15) as client:
                resp = await client.post(endpoint, params=params, json=payload)
        except Exception as exc:
            logger.debug("browserless call failed for %s: %s", req.url, exc)
            return AcquireResult(
                html="", final_url=req.url, strategy=self.name,
                challenge=ChallengeType.UNKNOWN, status_code=None,
                duration_ms=int((time.monotonic() - start) * 1000),
                note=str(exc),
            )

        elapsed = int((time.monotonic() - start) * 1000)
        if resp.status_code in (401, 403):
            return AcquireResult(
                html="", final_url=req.url, strategy=self.name,
                challenge=ChallengeType.HARD_BLOCK, status_code=resp.status_code,
                duration_ms=elapsed, note="browserless token rejected",
            )
        if resp.status_code != 200:
            return AcquireResult(
                html="", final_url=req.url, strategy=self.name,
                challenge=ChallengeType.UNKNOWN, status_code=resp.status_code,
                duration_ms=elapsed, note=f"browserless HTTP {resp.status_code}",
            )
        html = resp.text
        challenge = classify_html(html, exempt=exempt)
        return AcquireResult(
            html=html if challenge != ChallengeType.HARD_BLOCK else "",
            final_url=req.url,
            strategy=self.name,
            challenge=challenge,
            status_code=resp.status_code,
            duration_ms=elapsed,
        )
