"""Structured types shared across the import pipeline.

Acquisition (fetching raw HTML) is deliberately separated from extraction
(turning HTML into markdown). Each stage returns a structured object so the
orchestrator and the API can report exactly what happened without grepping logs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChallengeType(str, Enum):
    """Classification of why a fetched page is unusable, if any."""

    NONE = "none"
    SOFT_JS = "soft_js"            # SPA shell — JS injects content
    TURNSTILE = "turnstile"        # Cloudflare Turnstile / interstitial
    CAPTCHA = "captcha"            # explicit captcha challenge
    LOGIN = "login"                # login wall
    PAYWALL = "paywall"            # subscription required
    RATE_LIMIT = "rate_limit"      # 429 or "too many requests"
    HARD_BLOCK = "hard_block"      # 403 / access denied / regional block
    EMPTY_SHELL = "empty_shell"    # 200 OK but body has no content
    UNKNOWN = "unknown"


# A failure_reason kept for backward compatibility with the existing API contract.
# Mirrors the legacy value space the frontend already knows.
LEGACY_FAILURE_REASONS = {"javascript", "bot_challenge", "blocked", "empty"}


def challenge_to_legacy(c: ChallengeType) -> str | None:
    if c == ChallengeType.NONE:
        return None
    if c in (ChallengeType.SOFT_JS, ChallengeType.EMPTY_SHELL):
        return "javascript"
    if c in (ChallengeType.TURNSTILE, ChallengeType.CAPTCHA):
        return "bot_challenge"
    if c in (ChallengeType.HARD_BLOCK, ChallengeType.LOGIN, ChallengeType.PAYWALL, ChallengeType.RATE_LIMIT):
        return "blocked"
    return "empty"


@dataclass
class StageTiming:
    """Wall-clock budget for one stage (fetch / render / extract)."""

    name: str
    duration_ms: int
    ok: bool
    note: str = ""


@dataclass
class AcquireResult:
    """Output of a fetch strategy: raw HTML (or empty) plus diagnostics."""

    html: str
    final_url: str
    strategy: str
    challenge: ChallengeType
    status_code: int | None
    duration_ms: int
    note: str = ""
    screenshot_path: str | None = None

    @property
    def ok(self) -> bool:
        return bool(self.html) and self.challenge in (ChallengeType.NONE, ChallengeType.SOFT_JS)


@dataclass
class QualityScore:
    """How good the extracted body looks. Drives escalation decisions."""

    body_chars: int
    paragraphs: int

    def is_good(self) -> bool:
        return self.body_chars >= 1500 or self.paragraphs >= 6

    def is_ok(self) -> bool:
        return self.body_chars >= 200

    def value(self) -> float:
        # Normalised 0..1 for diagnostics / UI.
        return min(1.0, self.body_chars / 1500)


@dataclass
class ExtractionResult:
    """Output of the extraction stage: clean markdown plus metadata."""

    title: str
    excerpt: str
    body: str
    has_img: bool
    img_url: str | None
    quality: QualityScore
    extractor: str  # "trafilatura" | "readability" | "lxml" | "wikipedia" | "youtube"


@dataclass
class Diagnostics:
    """Full per-import diagnostics returned in API responses."""

    strategy: str = ""
    extractor: str = ""
    challenge: ChallengeType = ChallengeType.NONE
    quality: float = 0.0
    fetch_ms: int = 0
    render_ms: int = 0
    extract_ms: int = 0
    total_ms: int = 0
    fallback_count: int = 0
    stages: list[StageTiming] = field(default_factory=list)
    final_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "extractor": self.extractor,
            "challenge": self.challenge.value,
            "quality": round(self.quality, 3),
            "fetch_ms": self.fetch_ms,
            "render_ms": self.render_ms,
            "extract_ms": self.extract_ms,
            "total_ms": self.total_ms,
            "fallback_count": self.fallback_count,
            "final_url": self.final_url,
            "stages": [
                {"name": s.name, "duration_ms": s.duration_ms, "ok": s.ok, "note": s.note}
                for s in self.stages
            ],
        }


@dataclass
class ImportRequest:
    """Input to the orchestrator. Keeps env access in one place."""

    url: str
    camoufox_enabled: bool = False
    camoufox_url: str = ""
    camoufox_timeout: int = 60
    flaresolverr_url: str = ""
    browserless_enabled: bool = False
    browserless_url: str = ""
    browserless_token: str = ""
    browserless_timeout: int = 30
    static_fetch_timeout: int = 8
    playwright_enabled: bool = True


@dataclass
class ImportResult:
    """Final output. Backward-compatible dict view in `to_legacy_dict`."""

    title: str
    excerpt: str
    body: str
    has_img: bool
    img_url: str | None
    partial: bool
    failure_reason: str | None
    diagnostics: Diagnostics

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "excerpt": self.excerpt,
            "body": self.body,
            "has_img": self.has_img,
            "img_url": self.img_url,
            "partial": self.partial,
            "failure_reason": self.failure_reason,
            "diagnostics": self.diagnostics.to_dict(),
        }
