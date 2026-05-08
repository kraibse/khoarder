"""Tiered import orchestrator.

Picks the cheapest fetch strategy that has a real chance of succeeding for a
given URL, escalates only when the previous tier returned a low-quality / blocked
/ empty result, records per-origin success history so future imports short-
circuit, and emits structured diagnostics for the API.

Default ladder (when no profile hint exists):
    1. static_http      — plain async GET, ~1s for healthy sites
    2. playwright       — local Chromium render for SPA shells / soft JS
    3. camoufox         — stealth Firefox sidecar (Cloudflare-grade fingerprinting)
    4. browserless      — remote browser fallback, optional + token-gated
    5. flaresolverr     — last-resort Cloudflare challenge solver

Wikipedia and YouTube hit fast paths and never enter the ladder.
"""
from __future__ import annotations

import logging
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.imports import extractors, fast_paths
from app.services.imports import origin_profile as profile_svc
from app.services.imports.challenges import is_blocking, looks_like_spa_shell, needs_render
from app.services.imports.strategies import (
    BrowserlessStrategy,
    CamoufoxStrategy,
    FetchStrategy,
    FlareSolverrStrategy,
    PlaywrightStrategy,
    StaticHTTPStrategy,
)
from app.services.imports.types import (
    AcquireResult,
    ChallengeType,
    Diagnostics,
    ExtractionResult,
    ImportRequest,
    ImportResult,
    StageTiming,
    challenge_to_legacy,
)

logger = logging.getLogger(__name__)


# Ordered names — controls escalation when no profile hint exists.
_LADDER: tuple[str, ...] = ("static_http", "playwright", "camoufox", "browserless", "flaresolverr")


class ImportOrchestrator:
    """Stateful per-import driver. Cheap to construct."""

    def __init__(self, db: AsyncSession | None = None) -> None:
        self.db = db
        self._strategies: dict[str, FetchStrategy] = {
            "static_http": StaticHTTPStrategy(),
            "playwright": PlaywrightStrategy(),
            "camoufox": CamoufoxStrategy(),
            "browserless": BrowserlessStrategy(),
            "flaresolverr": FlareSolverrStrategy(),
        }

    async def run(self, req: ImportRequest) -> ImportResult:
        total_start = time.monotonic()
        diag = Diagnostics()

        # ── Fast paths ───────────────────────────────────────────────────────
        yt_id = fast_paths.youtube_video_id(req.url)
        if yt_id:
            data = await fast_paths.youtube_extract(yt_id)
            diag.strategy = "youtube"
            diag.extractor = "youtube"
            diag.total_ms = int((time.monotonic() - total_start) * 1000)
            return ImportResult(
                title=data["title"],
                excerpt=data["excerpt"],
                body=data["body"],
                has_img=data["has_img"],
                img_url=data["img_url"],
                partial=False,
                failure_reason=None,
                diagnostics=diag,
            )

        is_wiki = fast_paths.is_wikipedia(req.url)

        # ── Plan ladder using origin profile hint ────────────────────────────
        order = await self._plan_ladder(req)

        best_acquired: AcquireResult | None = None
        best_extraction: ExtractionResult | None = None
        last_challenge = ChallengeType.UNKNOWN
        last_strategy_used = ""
        fallback_count = 0

        for strategy_name in order:
            strategy = self._strategies.get(strategy_name)
            if strategy is None or not strategy.is_available(req):
                continue

            acquired = await strategy.fetch(req)
            last_strategy_used = strategy_name
            last_challenge = acquired.challenge
            self._record_stage(diag, strategy_name, acquired)

            if not acquired.html:
                fallback_count += 1
                if not is_blocking(acquired.challenge):
                    # Strategy errored (network/timeout) without a clear challenge — try next tier.
                    continue
                # Hard block / login / paywall — escalate.
                continue

            extraction_start = time.monotonic()
            extraction = extractors.extract_best(acquired.html, acquired.final_url, is_wikipedia=is_wiki)
            diag.extract_ms += int((time.monotonic() - extraction_start) * 1000)

            if best_extraction is None or extraction.quality.body_chars > best_extraction.quality.body_chars:
                best_acquired = acquired
                best_extraction = extraction

            if extraction.quality.is_good():
                break

            # Need-render / spa-shell / weak content → keep escalating to render tiers.
            if not needs_render(acquired.challenge) and not looks_like_spa_shell(acquired.html):
                if extraction.quality.is_ok() and not is_blocking(acquired.challenge):
                    # Decent body and the page isn't blocked — stop paying for browsers.
                    break
            fallback_count += 1

        diag.fallback_count = max(0, fallback_count)
        diag.total_ms = int((time.monotonic() - total_start) * 1000)

        if best_acquired is None or best_extraction is None or not best_extraction.body:
            return self._partial_result(req, diag, last_challenge, last_strategy_used)

        diag.strategy = best_acquired.strategy
        diag.extractor = best_extraction.extractor
        diag.challenge = best_acquired.challenge
        diag.quality = best_extraction.quality.value()
        diag.final_url = best_acquired.final_url

        await self._record_outcome_success(req, best_acquired.strategy)

        partial = not best_extraction.quality.is_ok()
        return ImportResult(
            title=best_extraction.title,
            excerpt=best_extraction.excerpt,
            body=best_extraction.body,
            has_img=best_extraction.has_img,
            img_url=best_extraction.img_url,
            partial=partial,
            failure_reason=challenge_to_legacy(best_acquired.challenge) if partial else None,
            diagnostics=diag,
        )

    # ── Internals ────────────────────────────────────────────────────────────
    async def _plan_ladder(self, req: ImportRequest) -> list[str]:
        if self.db is None:
            return list(_LADDER)
        preferred, skip_static = await profile_svc.hint_for(self.db, req.url)
        order: list[str] = []
        if preferred and preferred in self._strategies:
            order.append(preferred)
        for name in _LADDER:
            if name in order:
                continue
            if name == "static_http" and skip_static:
                continue
            order.append(name)
        return order

    def _record_stage(self, diag: Diagnostics, name: str, acquired: AcquireResult) -> None:
        diag.stages.append(
            StageTiming(
                name=name,
                duration_ms=acquired.duration_ms,
                ok=bool(acquired.html),
                note=acquired.note or acquired.challenge.value,
            )
        )
        if name == "static_http":
            diag.fetch_ms += acquired.duration_ms
        else:
            diag.render_ms += acquired.duration_ms

    async def _record_outcome_success(self, req: ImportRequest, strategy: str) -> None:
        if self.db is None:
            return
        try:
            await profile_svc.record_success(self.db, req.url, strategy)
        except Exception as exc:
            logger.debug("origin profile success record failed: %s", exc)

    async def _record_outcome_failure(self, req: ImportRequest, challenge: ChallengeType, strategy: str) -> None:
        if self.db is None:
            return
        try:
            await profile_svc.record_failure(self.db, req.url, challenge, strategy)
        except Exception as exc:
            logger.debug("origin profile failure record failed: %s", exc)

    def _partial_result(
        self,
        req: ImportRequest,
        diag: Diagnostics,
        last_challenge: ChallengeType,
        last_strategy: str,
    ) -> ImportResult:
        from urllib.parse import urlparse
        diag.strategy = last_strategy or "none"
        diag.extractor = "none"
        diag.challenge = last_challenge
        return ImportResult(
            title=urlparse(req.url).hostname or req.url,
            excerpt="",
            body="",
            has_img=False,
            img_url=None,
            partial=True,
            failure_reason=challenge_to_legacy(last_challenge) or "blocked",
            diagnostics=diag,
        )


async def import_url(req: ImportRequest, db: AsyncSession | None = None) -> ImportResult:
    """Module-level convenience wrapper: build an orchestrator, run, return result."""
    orch = ImportOrchestrator(db=db)
    result = await orch.run(req)
    if result.partial and db is not None:
        # Persist failure outcome so subsequent imports for the domain skip cooldowns appropriately.
        await orch._record_outcome_failure(req, result.diagnostics.challenge, result.diagnostics.strategy)
    return result
