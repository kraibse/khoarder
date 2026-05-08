"""Metadata extraction (og:title, og:description, og:image) shared by all extractors."""
from __future__ import annotations

import html as html_lib
import re
from urllib.parse import urljoin

_TITLE_RE = re.compile(r"<title[^>]*>([^<]+)</title>", re.IGNORECASE)
_OG_TITLE_RES = (
    re.compile(r'<meta\s[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:title["\']', re.IGNORECASE),
)
_DESC_RES = (
    re.compile(r'<meta\s[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']', re.IGNORECASE),
    re.compile(r'<meta\s[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:description["\']', re.IGNORECASE),
)
_IMG_RES = (
    re.compile(r'<meta\s[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', re.IGNORECASE),
    re.compile(r'<meta\s[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']twitter:image["\']', re.IGNORECASE),
)
_IMG_SKIP = (
    "arxiv-logo", "logo", "favicon", "icon", "avatar",
    "/static/", "/assets/logo", "site_icon", "apple-touch-icon",
)


def extract_meta(html: str, base_url: str = "") -> tuple[str, str, str | None]:
    """Return (title, description, img_url). Empty strings when absent."""
    title = ""
    description = ""
    img_url: str | None = None

    m = _TITLE_RE.search(html)
    if m:
        title = html_lib.unescape(m.group(1).strip())

    for pat in _OG_TITLE_RES:
        m = pat.search(html)
        if m:
            title = html_lib.unescape(m.group(1).strip()) or title
            break

    for pat in _DESC_RES:
        m = pat.search(html)
        if m:
            description = html_lib.unescape(m.group(1).strip())
            break

    for pat in _IMG_RES:
        m = pat.search(html)
        if not m:
            continue
        raw = m.group(1).strip()
        if raw and base_url:
            raw = urljoin(base_url, raw)
        if any(s in raw.lower() for s in _IMG_SKIP):
            raw = ""
        if raw:
            img_url = raw
        break

    return title, description, img_url
