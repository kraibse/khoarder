"""Local Playwright render — cheaper than Camoufox, used for SPA shells.

Optional dependency. When playwright isn't installed (or its browser binaries
are missing) the strategy reports `is_available=False` and the orchestrator
skips it cleanly without raising.
"""
from __future__ import annotations

import logging
import time

from app.services.imports.challenges import classify_html
from app.services.imports.fast_paths import is_wikipedia
from app.services.imports.strategies.base import FetchStrategy
from app.services.imports.types import AcquireResult, ChallengeType, ImportRequest

logger = logging.getLogger(__name__)


def _playwright_importable() -> bool:
    try:
        import playwright.async_api  # noqa: F401
        return True
    except ImportError:
        return False


class PlaywrightStrategy(FetchStrategy):
    name = "playwright"

    def is_available(self, req: ImportRequest) -> bool:
        return req.playwright_enabled and _playwright_importable()

    async def fetch(self, req: ImportRequest) -> AcquireResult:
        start = time.monotonic()
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return AcquireResult(
                html="", final_url=req.url, strategy=self.name,
                challenge=ChallengeType.UNKNOWN, status_code=None,
                duration_ms=0, note="playwright not installed",
            )

        exempt = is_wikipedia(req.url)
        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                )
                page = await ctx.new_page()
                resp = await page.goto(
                    req.url,
                    wait_until="networkidle",
                    timeout=req.camoufox_timeout * 1000,
                )
                # Small idle pad for late-mounting frameworks.
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5_000)
                except Exception:
                    pass
                html = await page.content()
                final_url = page.url
                status = resp.status if resp else None
                await ctx.close()
                await browser.close()
        except Exception as exc:
            logger.debug("playwright failed for %s: %s", req.url, exc)
            return AcquireResult(
                html="", final_url=req.url, strategy=self.name,
                challenge=ChallengeType.UNKNOWN, status_code=None,
                duration_ms=int((time.monotonic() - start) * 1000),
                note=str(exc),
            )

        elapsed = int((time.monotonic() - start) * 1000)
        challenge = classify_html(html, status_code=status, exempt=exempt)
        return AcquireResult(
            html=html if challenge != ChallengeType.HARD_BLOCK else "",
            final_url=final_url,
            strategy=self.name,
            challenge=challenge,
            status_code=status,
            duration_ms=elapsed,
        )
