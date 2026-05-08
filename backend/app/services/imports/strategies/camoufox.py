"""Camoufox stealth-browser sidecar fetch."""
from __future__ import annotations

import logging
import time

import httpx

from app.services.imports.challenges import classify_html
from app.services.imports.fast_paths import is_wikipedia
from app.services.imports.strategies.base import FetchStrategy
from app.services.imports.types import AcquireResult, ChallengeType, ImportRequest

logger = logging.getLogger(__name__)


class CamoufoxStrategy(FetchStrategy):
    name = "camoufox"

    def is_available(self, req: ImportRequest) -> bool:
        return req.camoufox_enabled and bool(req.camoufox_url.strip())

    async def fetch(self, req: ImportRequest) -> AcquireResult:
        start = time.monotonic()
        exempt = is_wikipedia(req.url)
        url = req.camoufox_url.rstrip("/") + "/fetch"
        try:
            async with httpx.AsyncClient(timeout=req.camoufox_timeout + 15) as client:
                resp = await client.post(
                    url,
                    json={"url": req.url, "timeout": req.camoufox_timeout},
                )
            data = resp.json()
        except Exception as exc:
            logger.debug("camoufox fetch failed for %s: %s", req.url, exc)
            return AcquireResult(
                html="", final_url=req.url, strategy=self.name,
                challenge=ChallengeType.UNKNOWN, status_code=None,
                duration_ms=int((time.monotonic() - start) * 1000),
                note=str(exc),
            )

        elapsed = int((time.monotonic() - start) * 1000)
        if data.get("status") != "ok":
            return AcquireResult(
                html="", final_url=req.url, strategy=self.name,
                challenge=ChallengeType.UNKNOWN, status_code=None,
                duration_ms=elapsed,
                note=str(data.get("message", "camoufox error")),
            )
        html = data.get("html", "")
        sidecar_says_challenge = bool(data.get("challenge"))
        challenge = classify_html(html, exempt=exempt)
        if sidecar_says_challenge and challenge == ChallengeType.NONE:
            challenge = ChallengeType.TURNSTILE
        return AcquireResult(
            html=html if challenge != ChallengeType.HARD_BLOCK else "",
            final_url=data.get("final_url", req.url),
            strategy=self.name,
            challenge=challenge,
            status_code=200,
            duration_ms=elapsed,
        )
