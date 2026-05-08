"""FlareSolverr fetch — last-resort Cloudflare challenge solver."""
from __future__ import annotations

import logging
import time

import httpx

from app.services.imports.challenges import classify_html
from app.services.imports.fast_paths import is_wikipedia
from app.services.imports.strategies.base import FetchStrategy
from app.services.imports.types import AcquireResult, ChallengeType, ImportRequest

logger = logging.getLogger(__name__)


class FlareSolverrStrategy(FetchStrategy):
    name = "flaresolverr"

    def is_available(self, req: ImportRequest) -> bool:
        return bool(req.flaresolverr_url.strip())

    async def fetch(self, req: ImportRequest) -> AcquireResult:
        start = time.monotonic()
        exempt = is_wikipedia(req.url)
        endpoint = req.flaresolverr_url.rstrip("/") + "/v1"
        payload = {
            "cmd": "request.get",
            "url": req.url,
            "maxTimeout": req.camoufox_timeout * 1000,
        }
        try:
            async with httpx.AsyncClient(timeout=req.camoufox_timeout + 15) as client:
                resp = await client.post(endpoint, json=payload)
            data = resp.json()
        except Exception as exc:
            logger.debug("flaresolverr call failed for %s: %s", req.url, exc)
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
                duration_ms=elapsed, note=str(data.get("message", "flaresolverr error")),
            )
        solution = data.get("solution", {}) or {}
        html = solution.get("response", "")
        challenge = classify_html(html, exempt=exempt)
        return AcquireResult(
            html=html if challenge != ChallengeType.HARD_BLOCK else "",
            final_url=solution.get("url", req.url),
            strategy=self.name,
            challenge=challenge,
            status_code=solution.get("status"),
            duration_ms=elapsed,
        )
