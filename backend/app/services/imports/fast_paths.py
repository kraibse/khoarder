"""Domain-specific fast paths bypass the strategy ladder entirely.

Wikipedia returns clean HTML over plain HTTP and is parseable without JS.
YouTube exposes oEmbed metadata + a transcript endpoint, so a single API
call beats running a browser.
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


def is_wikipedia(url: str) -> bool:
    return "wikipedia.org" in url or "wikimedia.org" in url


def youtube_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [""])[0] or None
        if parsed.path.startswith("/embed/") or parsed.path.startswith("/shorts/"):
            return parsed.path.split("/")[2] or None
    elif host == "youtu.be":
        return parsed.path.lstrip("/") or None
    return None


async def youtube_extract(video_id: str) -> dict:
    """Build a YouTube entry: oEmbed metadata + embed iframe + transcript (if available).

    Intentionally does NOT call the LLM — auto-summarisation belongs to a
    user-triggered AI assist action, not the import path.
    """
    import httpx

    result: dict = {
        "title": f"YouTube video {video_id}",
        "excerpt": "",
        "body": "",
        "has_img": True,
        "img_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "partial": False,
        "failure_reason": None,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://www.youtube.com/oembed",
                params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                result["title"] = data.get("title", result["title"])
                result["excerpt"] = data.get("author_name", "")
    except Exception as exc:
        logger.debug("youtube oembed failed for %s: %s", video_id, exc)

    transcript_text = ""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join(item["text"] for item in transcript_list)
    except ImportError:
        logger.debug("youtube_transcript_api not installed")
    except Exception as exc:
        logger.debug("youtube transcript failed for %s: %s", video_id, exc)

    embed = (
        f'<iframe width="100%" height="400" '
        f'src="https://www.youtube.com/embed/{video_id}" '
        f'frameborder="0" allowfullscreen></iframe>'
    )
    parts = [embed]
    if transcript_text:
        parts.append(f"\n\n## Transcript\n\n{transcript_text[:6000]}")
    result["body"] = "\n".join(parts)
    return result
