"""Offline tests for the tiered URL import pipeline.

Covers the parts that don't need network: challenge classification, extraction
fallback ordering, orchestrator ladder planning. Strategy fetches are exercised
through a fake strategy injected into ImportOrchestrator.
"""
from __future__ import annotations

import asyncio
import unittest

from app.services.imports import (
    AcquireResult,
    ChallengeType,
    ImportOrchestrator,
    ImportRequest,
)
from app.services.imports.challenges import (
    classify_html,
    is_blocking,
    looks_like_spa_shell,
    needs_render,
)
from app.services.imports import extractors
from app.services.imports.strategies.base import FetchStrategy


_ARTICLE = (
    "<html><head><title>Sample</title>"
    '<meta property="og:description" content="lead paragraph">'
    "</head><body><article>"
    + "<p>" + ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10) + "</p>" * 6
    + "</article></body></html>"
)
_TURNSTILE = (
    "<html><head><title>Just a moment...</title></head><body>"
    "Checking your browser. Cloudflare ray id 1234"
    "</body></html>"
)
_SPA_SHELL = (
    "<!DOCTYPE html><html><head><title>App</title></head>"
    '<body><div id="root"></div><script src="/main.js"></script></body></html>'
)


class ChallengeClassifierTests(unittest.TestCase):
    def test_real_article_is_clean(self):
        self.assertEqual(classify_html(_ARTICLE), ChallengeType.NONE)

    def test_cloudflare_turnstile(self):
        self.assertEqual(classify_html(_TURNSTILE), ChallengeType.TURNSTILE)

    def test_429_rate_limit(self):
        self.assertEqual(classify_html("", status_code=429), ChallengeType.RATE_LIMIT)

    def test_spa_shell_is_empty(self):
        self.assertEqual(classify_html(_SPA_SHELL), ChallengeType.EMPTY_SHELL)
        self.assertTrue(looks_like_spa_shell(_SPA_SHELL))

    def test_wikipedia_exempt(self):
        # Wikipedia article body legitimately contains words like "blocked".
        self.assertEqual(
            classify_html("<html>access denied blocked</html>", exempt=True),
            ChallengeType.NONE,
        )

    def test_helpers(self):
        self.assertTrue(is_blocking(ChallengeType.TURNSTILE))
        self.assertTrue(is_blocking(ChallengeType.HARD_BLOCK))
        self.assertFalse(is_blocking(ChallengeType.NONE))
        self.assertTrue(needs_render(ChallengeType.SOFT_JS))
        self.assertTrue(needs_render(ChallengeType.EMPTY_SHELL))


class ExtractorTests(unittest.TestCase):
    def test_trafilatura_or_fallback_returns_body(self):
        result = extractors.extract_best(_ARTICLE, "https://example.com")
        self.assertGreater(result.quality.body_chars, 200)
        self.assertIn(result.extractor, {"trafilatura", "readability", "lxml"})

    def test_empty_shell_returns_zero_body(self):
        result = extractors.extract_best(_SPA_SHELL, "https://example.com")
        self.assertEqual(result.body, "")
        self.assertEqual(result.extractor, "none")


class _FakeStrategy(FetchStrategy):
    """Records every call and returns whatever AcquireResult was queued."""

    def __init__(self, name: str, results: list[AcquireResult]):
        self.name = name
        self._results = list(results)
        self.calls = 0

    def is_available(self, req: ImportRequest) -> bool:
        return True

    async def fetch(self, req: ImportRequest) -> AcquireResult:
        self.calls += 1
        return self._results.pop(0)


def _ok(strategy: str, html: str) -> AcquireResult:
    return AcquireResult(
        html=html, final_url="https://example.com", strategy=strategy,
        challenge=ChallengeType.NONE, status_code=200, duration_ms=10,
    )


def _blocked(strategy: str, kind: ChallengeType = ChallengeType.TURNSTILE) -> AcquireResult:
    return AcquireResult(
        html="", final_url="https://example.com", strategy=strategy,
        challenge=kind, status_code=403, duration_ms=10,
    )


class OrchestratorTests(unittest.TestCase):
    def test_default_ladder_no_db(self):
        async def go():
            orch = ImportOrchestrator(db=None)
            order = await orch._plan_ladder(ImportRequest(url="https://example.com"))
            return order
        order = asyncio.run(go())
        self.assertEqual(order, ["static_http", "playwright", "camoufox", "browserless", "flaresolverr"])

    def test_static_success_short_circuits(self):
        async def go():
            orch = ImportOrchestrator(db=None)
            static = _FakeStrategy("static_http", [_ok("static_http", _ARTICLE)])
            never = _FakeStrategy("camoufox", [_ok("camoufox", _ARTICLE)])
            orch._strategies["static_http"] = static
            orch._strategies["camoufox"] = never
            orch._strategies["playwright"] = _FakeStrategy("playwright", [_ok("playwright", _ARTICLE)])
            orch._strategies["browserless"] = _FakeStrategy("browserless", [_ok("browserless", _ARTICLE)])
            orch._strategies["flaresolverr"] = _FakeStrategy("flaresolverr", [_ok("flaresolverr", _ARTICLE)])
            return await orch.run(ImportRequest(url="https://example.com")), never
        result, never = asyncio.run(go())
        self.assertEqual(result.diagnostics.strategy, "static_http")
        self.assertFalse(result.partial)
        self.assertEqual(never.calls, 0, "later tier should not have been called once static succeeded")

    def test_escalation_on_blocked(self):
        async def go():
            orch = ImportOrchestrator(db=None)
            orch._strategies["static_http"] = _FakeStrategy("static_http", [_blocked("static_http")])
            orch._strategies["playwright"] = _FakeStrategy("playwright", [_blocked("playwright")])
            orch._strategies["camoufox"] = _FakeStrategy("camoufox", [_ok("camoufox", _ARTICLE)])
            orch._strategies["browserless"] = _FakeStrategy("browserless", [_ok("browserless", _ARTICLE)])
            orch._strategies["flaresolverr"] = _FakeStrategy("flaresolverr", [_ok("flaresolverr", _ARTICLE)])
            return await orch.run(ImportRequest(url="https://example.com"))
        result = asyncio.run(go())
        self.assertEqual(result.diagnostics.strategy, "camoufox")
        self.assertGreaterEqual(result.diagnostics.fallback_count, 2)
        self.assertFalse(result.partial)

    def test_all_blocked_returns_partial(self):
        async def go():
            orch = ImportOrchestrator(db=None)
            for n in ("static_http", "playwright", "camoufox", "browserless", "flaresolverr"):
                orch._strategies[n] = _FakeStrategy(n, [_blocked(n)])
            return await orch.run(ImportRequest(url="https://example.com"))
        result = asyncio.run(go())
        self.assertTrue(result.partial)
        self.assertEqual(result.failure_reason, "bot_challenge")
        self.assertEqual(result.body, "")


if __name__ == "__main__":
    unittest.main()
