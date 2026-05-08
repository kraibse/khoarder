"""Structured challenge classifier.

Replaces the boolean `_is_bot_challenge` heuristic from the legacy entries
extractor with a typed classifier so the orchestrator can branch by reason
and the API can show the user *why* an import was blocked.

Wikipedia is exempted at the call site (orchestrator.py) — the same body
text patterns that flag bot pages legitimately appear in Wikipedia articles
about Cloudflare, captchas, blocked URLs, etc.
"""
from __future__ import annotations

import re

from app.services.imports.types import ChallengeType


# Substrings grouped by classification. Lowercase compared.
_PATTERNS: list[tuple[ChallengeType, tuple[str, ...]]] = [
    (
        ChallengeType.TURNSTILE,
        (
            "just a moment",
            "checking your browser",
            "performing security verification",
            "ddos protection",
            "ray id",
            "cf-chl-bypass",
            "__cf_chl",
            "cloudflare",
        ),
    ),
    (
        ChallengeType.CAPTCHA,
        (
            "captcha",
            "i'm not a robot",
            "you're not a robot",
            "you are not a robot",
            "verify you are human",
            "verify you're human",
            "human verification",
            "robot verification",
            "g-recaptcha",
            "h-captcha",
        ),
    ),
    (
        ChallengeType.LOGIN,
        (
            "please sign in",
            "please log in",
            "sign in to continue",
            "log in to continue",
            "you must be logged in",
        ),
    ),
    (
        ChallengeType.PAYWALL,
        (
            "subscribe to read",
            "subscriber-only",
            "this article is for subscribers",
            "subscription required",
            "become a member",
        ),
    ),
    (
        ChallengeType.RATE_LIMIT,
        (
            "too many requests",
            "rate limit",
            "you have been rate limited",
            "slow down",
        ),
    ),
    (
        ChallengeType.HARD_BLOCK,
        (
            "access denied",
            "you don't have permission",
            "403 forbidden",
            "your access to this site has been limited",
            "blocked",
            "unusual traffic",
            "automated access",
        ),
    ),
]


def classify_html(html: str, status_code: int | None = None, *, exempt: bool = False) -> ChallengeType:
    """Classify a fetched response. `exempt=True` short-circuits to NONE."""
    if exempt:
        return ChallengeType.NONE

    if status_code is not None:
        if status_code == 429:
            return ChallengeType.RATE_LIMIT
        if status_code in (401, 403):
            return ChallengeType.HARD_BLOCK

    if not html:
        return ChallengeType.HARD_BLOCK

    lower = html.lower()
    for kind, patterns in _PATTERNS:
        if any(p in lower for p in patterns):
            return kind

    if _is_empty_shell(html):
        return ChallengeType.EMPTY_SHELL

    return ChallengeType.NONE


_SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")


def _is_empty_shell(html: str) -> bool:
    """Heuristic: 200 OK SPA whose <body> has < 200 chars of plain text."""
    stripped = _SCRIPT_RE.sub(" ", html)
    stripped = _STYLE_RE.sub(" ", stripped)
    body_match = _BODY_RE.search(stripped)
    candidate = body_match.group(1) if body_match else stripped
    text_only = _TAG_RE.sub(" ", candidate)
    text_only = re.sub(r"\s+", " ", text_only).strip()
    return len(text_only) < 200


def looks_like_spa_shell(html: str) -> bool:
    """Public helper kept for the orchestrator's escalation decisions."""
    return _is_empty_shell(html)


def is_blocking(challenge: ChallengeType) -> bool:
    """True when extraction cannot recover from this challenge — must escalate."""
    return challenge in (
        ChallengeType.TURNSTILE,
        ChallengeType.CAPTCHA,
        ChallengeType.LOGIN,
        ChallengeType.PAYWALL,
        ChallengeType.RATE_LIMIT,
        ChallengeType.HARD_BLOCK,
    )


def needs_render(challenge: ChallengeType) -> bool:
    """True when a JS-capable browser is likely to recover content."""
    return challenge in (ChallengeType.SOFT_JS, ChallengeType.EMPTY_SHELL)
