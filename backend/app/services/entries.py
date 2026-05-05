import re
import uuid

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.relation import Relation
from app.models.tag import Tag, entry_tags
from app.schemas.entry import ArticleDetailOut, BacklinkOut, EntryOut, EntryUpdate, RelatedEntryOut
from app.schemas.attachment import AttachmentOut


def _format_date(dt) -> str:
    return dt.strftime("%b %d, %Y") if dt else ""


def _entry_source(entry: Entry) -> str | None:
    return entry.source_label or entry.source_url or None


async def _backlink_count(db: AsyncSession, entry_id: str) -> int:
    result = await db.execute(
        select(func.count()).where(Relation.to_entry_id == entry_id, Relation.kind == "backlink")
    )
    return result.scalar_one()


async def _to_entry_out(
    db: AsyncSession,
    entry: Entry,
    headline: str | None = None,
    headlines: list[str] | None = None,
    match_count: int = 0,
) -> EntryOut:
    return EntryOut(
        id=entry.id,
        topic_id=entry.topic_id,
        type=entry.type,
        title=entry.title,
        excerpt=entry.excerpt,
        tags=[t.name for t in entry.tags],
        date=_format_date(entry.created_at),
        source=_entry_source(entry),
        has_img=entry.has_img,
        img_url=entry.img_url,
        img_height=entry.img_height,
        img_color=entry.img_color,
        is_starred=entry.is_starred,
        backlink_count=await _backlink_count(db, entry.id),
        headline=headline,
        headlines=headlines or [],
        match_count=match_count,
    )


async def list_entries(
    db: AsyncSession,
    topic_id: str | None = None,
    entry_type: str | None = None,
    sort: str = "date_desc",
    q: str | None = None,
    tag: str | None = None,
) -> list[EntryOut]:
    # Search mode: delegate to pluggable FTS backend
    if q:
        from app.services import search as search_svc

        hits = await search_svc.search(db, q, topic_id=topic_id, entry_type=entry_type)
        out = []
        for hit in hits:
            entry = hit.entry
            if tag and not any(t.name == tag for t in entry.tags):
                continue
            out.append(await _to_entry_out(
                db, entry,
                headline=hit.headline,
                headlines=hit.headlines,
                match_count=hit.match_count,
            ))
        if sort == "backlinks_desc":
            out.sort(key=lambda e: e.backlink_count, reverse=True)
        return out

    # Browse mode: standard ordered query
    stmt = select(Entry).options(selectinload(Entry.tags))

    if topic_id:
        stmt = stmt.where(Entry.topic_id == topic_id)
    if entry_type and entry_type.lower() != "all":
        singular = entry_type.rstrip("s")
        stmt = stmt.where(Entry.type.ilike(f"{singular}%"))
    if tag:
        stmt = stmt.join(entry_tags, Entry.id == entry_tags.c.entry_id).join(
            Tag, Tag.id == entry_tags.c.tag_id
        ).where(Tag.name == tag)

    if sort == "date_asc":
        stmt = stmt.order_by(Entry.created_at.asc())
    elif sort == "title_asc":
        stmt = stmt.order_by(Entry.title.asc())
    else:
        stmt = stmt.order_by(Entry.created_at.desc())

    result = await db.execute(stmt)
    entries = result.scalars().all()
    out = [await _to_entry_out(db, e) for e in entries]

    if sort == "backlinks_desc":
        out.sort(key=lambda e: e.backlink_count, reverse=True)

    return out


async def get_entry(db: AsyncSession, entry_id: str) -> ArticleDetailOut | None:
    result = await db.execute(
        select(Entry).options(selectinload(Entry.tags)).where(Entry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return None

    return ArticleDetailOut(
        id=entry.id,
        topic_id=entry.topic_id,
        type=entry.type,
        title=entry.title,
        excerpt=entry.excerpt,
        body=entry.body,
        tags=[t.name for t in entry.tags],
        date=_format_date(entry.created_at),
        source=_entry_source(entry),
        source_url=entry.source_url,
        has_img=entry.has_img,
        img_url=entry.img_url,
        img_height=entry.img_height,
        img_color=entry.img_color,
        word_count=entry.word_count,
        read_time_min=entry.read_time_min,
        backlink_count=await _backlink_count(db, entry.id),
    )


async def get_backlinks(db: AsyncSession, entry_id: str) -> list[BacklinkOut]:
    result = await db.execute(
        select(Relation)
        .options(selectinload(Relation.from_entry).selectinload(Entry.tags))
        .where(Relation.to_entry_id == entry_id, Relation.kind == "backlink")
    )
    relations = result.scalars().all()

    out = []
    for rel in relations:
        e = rel.from_entry
        refs = await _backlink_count(db, e.id)
        out.append(BacklinkOut(id=e.id, relation_id=rel.id, title=e.title, type=e.type, refs=refs))
    return out


async def get_related(db: AsyncSession, entry_id: str) -> list[RelatedEntryOut]:
    result = await db.execute(
        select(Relation)
        .options(selectinload(Relation.to_entry))
        .where(Relation.from_entry_id == entry_id, Relation.kind == "related")
    )
    relations = result.scalars().all()

    out = []
    for rel in relations:
        e = rel.to_entry
        out.append(RelatedEntryOut(id=e.id, relation_id=rel.id, title=e.title, type=e.type, img_color=e.img_color))
    return out


async def get_attachments(db: AsyncSession, entry_id: str) -> list[AttachmentOut]:
    from app.models.attachment import Attachment

    result = await db.execute(
        select(Attachment).where(Attachment.entry_id == entry_id).order_by(Attachment.created_at)
    )
    return [
        AttachmentOut(
            id=a.id,
            filename=a.filename,
            ext=a.ext,
            size_bytes=a.size_bytes,
            created_at=a.created_at,
        )
        for a in result.scalars().all()
    ]


async def list_all_tags(db: AsyncSession) -> list[str]:
    result = await db.execute(select(Tag.name).order_by(Tag.name))
    return list(result.scalars().all())


# Palette for auto-assigning img_color to new entries
_IMG_COLORS = [
    "oklch(72% 0.08 200)", "oklch(65% 0.10 160)", "oklch(68% 0.07 30)",
    "oklch(60% 0.09 280)", "oklch(74% 0.06 80)", "oklch(62% 0.11 320)",
    "oklch(70% 0.08 120)", "oklch(67% 0.09 240)", "oklch(75% 0.05 50)",
    "oklch(63% 0.10 190)", "oklch(71% 0.07 340)", "oklch(66% 0.08 100)",
]


async def _classify_entry(db: AsyncSession, title: str, excerpt: str, body: str) -> tuple[str | None, str | None]:
    """Use LM Studio to classify an entry into a topic. Returns (topic_id, topic_name) or (None, None)."""
    import logging
    from app.core.config import settings
    from app.services import config as config_svc
    from app.models.topic import Topic

    logger = logging.getLogger(__name__)

    base_url = await config_svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    if not base_url or not base_url.strip():
        return None, None

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            base_url=base_url.rstrip("/") + "/",
            api_key="not-needed",
            timeout=float(await config_svc.get_config_value(db, "llm_timeout", default=str(settings.llm_timeout))),
        )
        model = await config_svc.get_config_value(db, "llm_model", default=settings.llm_model)

        # Get existing topics
        topics_result = await db.execute(select(Topic).order_by(Topic.name))
        topics = topics_result.scalars().all()
        topic_list = ", ".join([f"{t.name}" for t in topics]) if topics else "none"

        prompt = (
            f"Classify the following knowledge entry into one of these existing topics: {topic_list}\n\n"
            f"If none fit, suggest a new short topic name (2-3 words).\n\n"
            f"Title: {title}\n"
            f"Excerpt: {excerpt}\n"
            f"Body: {body[:500]}...\n\n"
            f"Respond with ONLY the topic name, nothing else."
        )

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=50,
        )
        raw_content = response.choices[0].message.content
        suggested = raw_content.strip() if raw_content else ""

        if not suggested:
            logger.warning("LM Studio returned empty topic suggestion")
            return None, None

        # Find matching topic (case-insensitive)
        suggested_lower = suggested.lower()
        for t in topics:
            if t.name.lower() == suggested_lower:
                return t.id, t.name

        # Create new topic
        import re
        slug = re.sub(r'[^\w\s-]', '', suggested_lower).strip()
        slug = re.sub(r'[-\s]+', '-', slug)[:64]
        if not slug:
            slug = "topic"
        # Ensure unique slug
        base_slug = slug
        counter = 1
        while True:
            existing = await db.execute(select(Topic).where(Topic.slug == slug))
            if existing.scalar_one_or_none() is None:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        import random
        colors = [
            "oklch(72% 0.08 200)", "oklch(65% 0.10 160)", "oklch(68% 0.07 30)",
            "oklch(60% 0.09 280)", "oklch(74% 0.06 80)", "oklch(62% 0.11 320)",
            "oklch(70% 0.08 120)", "oklch(67% 0.09 240)", "oklch(75% 0.05 50)",
        ]
        new_topic = Topic(
            id=str(uuid.uuid4()),
            slug=slug,
            name=suggested,
            color=random.choice(colors),
            description="",
        )
        db.add(new_topic)
        await db.flush()
        return new_topic.id, new_topic.name
    except Exception as exc:
        logger.warning("Auto-categorization failed: %s", exc)
        return None, None


def _meta_extract(html: str) -> tuple[str, str, str | None]:
    """Extract og:title (or <title>), meta description, og:image from raw HTML.
    Returns (title, description, img_url)."""
    import re
    import html as html_lib

    title = ""
    description = ""
    img_url = None

    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if m:
        title = html_lib.unescape(m.group(1).strip())

    for pat in [
        r'<meta\s[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:title["\']',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            title = html_lib.unescape(m.group(1).strip()) or title
            break

    for pat in [
        r'<meta\s[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']',
        r'<meta\s[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:description["\']',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            description = html_lib.unescape(m.group(1).strip())
            break

    for pat in [
        r'<meta\s[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
        r'<meta\s[^>]*name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)["\']',
        r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']twitter:image["\']',
    ]:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            img_url = m.group(1).strip()
            break

    return title, description, img_url


def _extract_lxml_fallback(html: str, url: str) -> str:
    """Last-resort extractor using lxml XPath: targets <article>, <main>, common content divs."""
    import re
    try:
        from lxml.html import fromstring

        doc = fromstring(html.encode("utf-8", errors="replace"))

        # Strip noise elements
        for tag in ("script", "style", "nav", "footer", "header", "aside", "noscript"):
            for el in doc.findall(f".//{tag}"):
                p = el.getparent()
                if p is not None:
                    p.remove(el)

        # Find main content area in priority order
        content = None
        xpaths = [
            '//article',
            '//main',
            '//*[@role="main"]',
            '//*[@id="content"]',
            '//*[contains(@class,"article-body")]',
            '//*[contains(@class,"article-content")]',
            '//*[contains(@class,"entry-content")]',
            '//*[contains(@class,"post-content")]',
            '//*[contains(@class,"content-body")]',
            '//*[contains(@class,"page-content")]',
            '//*[contains(@class,"story-body")]',
            '//*[contains(@class,"body-content")]',
        ]
        for xpath in xpaths:
            els = doc.xpath(xpath)
            if els:
                content = max(els, key=lambda e: len((e.text_content() or "")))
                break

        if content is None:
            body_el = doc.find(".//body")
            content = body_el if body_el is not None else doc

        parts: list[str] = []
        seen: set[str] = set()

        for el in content.iter():
            tag = el.tag if isinstance(el.tag, str) else ""
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                text = (el.text_content() or "").strip()
                if text and text not in seen and len(text) > 2:
                    seen.add(text)
                    level = int(tag[1])
                    parts.append(f"\n{'#' * level} {text}\n")
            elif tag == "p":
                text = (el.text_content() or "").strip()
                if len(text) > 30 and text not in seen:
                    seen.add(text)
                    parts.append(text + "\n\n")

        result = "".join(parts)
        result = re.sub(r"\n{3,}", "\n\n", result).strip()
        return result
    except ImportError:
        return ""
    except Exception:
        return ""


async def extract_url_content(
    url: str,
    camoufox_enabled: bool = False,
    camoufox_timeout: int = 30,
    camoufox_url: str = "",
) -> dict:
    """Fetch and extract content from a URL using a layered extraction strategy.

    Layers (in order):
    1. trafilatura — ML heuristic extractor, handles most news/article sites
    2. readability-lxml — Mozilla Readability algorithm
    3. lxml XPath — targets <article>/<main>/role=main and known content class names
    4. camoufox-browser sidecar (optional) — stealth headless browser accessed via HTTP

    Returns dict: title, excerpt, body, has_img, img_url, partial.
    partial=True signals the body is sparse and the user may want to paste content.
    """
    import re
    import logging
    from urllib.parse import urlparse
    import httpx

    logger = logging.getLogger(__name__)

    _BROWSER_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
    }

    parsed = urlparse(url)
    title = parsed.hostname or url
    excerpt = ""
    body = ""
    has_img = False
    img_url = None

    # ── Fetch ────────────────────────────────────────────────────────────────────
    html = ""
    fetch_failed = False
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resp = await client.get(url, headers=_BROWSER_HEADERS)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:
        logger.warning("URL fetch failed for %s: %s", url, exc)
        fetch_failed = True

    # ── Camoufox fallback when static fetch fails ────────────────────────────────
    if fetch_failed and camoufox_enabled and camoufox_url:
        try:
            logger.debug("static fetch failed, trying camoufox-browser sidecar for %s", url)
            async with httpx.AsyncClient(timeout=camoufox_timeout + 10) as cf_client:
                cf_resp = await cf_client.post(
                    camoufox_url.rstrip("/") + "/fetch",
                    json={"url": url, "timeout": camoufox_timeout},
                )
            cf_data = cf_resp.json()
            if cf_data.get("status") == "ok":
                html = cf_data.get("html", "")
                logger.debug("camoufox fetch succeeded for %s (%d bytes)", url, len(html))
            else:
                logger.warning("camoufox-browser error for %s: %s", url, cf_data.get("message"))
        except Exception as exc:
            logger.warning("camoufox-browser call failed for %s: %s", url, exc)

    if not html:
        return {"title": title, "excerpt": "", "body": "", "has_img": False, "img_url": None, "partial": True}

    # ── Meta (title / description / image) ───────────────────────────────────────
    meta_title, meta_desc, meta_img = _meta_extract(html)
    if meta_title:
        title = meta_title
    if meta_desc:
        excerpt = meta_desc
    if meta_img:
        has_img = True
        img_url = meta_img

    is_wikipedia = "wikipedia.org" in url or "wikimedia.org" in url

    # ── Wikipedia fast-path (unchanged, known-good) ──────────────────────────────
    if is_wikipedia:
        import re as _re
        from html.parser import HTMLParser

        content_match = _re.search(
            r'<div[^>]*id=["\']mw-content-text["\'][^>]*>(.*?)</div>\s*'
            r'(?:<div[^>]*class=["\']catlinks["\']|<div[^>]*id=["\']mw-data-after-content["\']|</body>)',
            html, _re.IGNORECASE | _re.DOTALL,
        )
        feed = content_match.group(1) if content_match else html

        class _WikiStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts: list[str] = []
                self.skip = 0
                self.in_p = False
                self.in_h = False
                self.hlevel = 0

            def handle_starttag(self, tag, attrs):
                ad = dict(attrs)
                if tag in ("script", "style", "nav", "footer", "header", "aside"):
                    self.skip += 1
                elif tag == "p":
                    cls = ad.get("class", "")
                    self.in_p = not any(c in cls for c in ("reference", "navbox", "infobox", "mw-empty-elt"))
                elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    self.in_h = True
                    self.hlevel = int(tag[1])
                elif tag in ("br", "div"):
                    self.parts.append("\n")

            def handle_endtag(self, tag):
                if tag in ("script", "style", "nav", "footer", "header", "aside"):
                    self.skip -= 1
                elif tag == "p":
                    if self.in_p and self.skip == 0:
                        self.parts.append("\n\n")
                    self.in_p = False
                elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    if self.in_h and self.skip == 0:
                        self.parts.append("\n\n")
                    self.in_h = False

            def handle_data(self, data):
                if self.skip:
                    return
                if self.in_h:
                    prefix = "#" * self.hlevel + " "
                    self.parts.append((prefix if not self.parts or self.parts[-1].endswith("\n") else "") + data)
                elif self.in_p:
                    self.parts.append(data)

            def get_text(self):
                return _re.sub(r"\n\s*\n", "\n\n", "".join(self.parts)).strip()

        s = _WikiStripper()
        s.feed(feed)
        body = s.get_text()

    else:
        # ── Layer 1: trafilatura ─────────────────────────────────────────────────
        try:
            import trafilatura
            extracted = trafilatura.extract(
                html,
                url=url,
                include_comments=False,
                include_tables=True,
                favor_recall=True,
                output_format="markdown",
            )
            if extracted and len(extracted.strip()) > 150:
                body = extracted.strip()
                logger.debug("trafilatura succeeded for %s (%d chars)", url, len(body))
        except ImportError:
            logger.debug("trafilatura not installed")
        except Exception as exc:
            logger.debug("trafilatura failed for %s: %s", url, exc)

        # ── Layer 2: readability-lxml ────────────────────────────────────────────
        if not body or len(body) < 150:
            try:
                from readability import Document
                import html as _html_lib

                doc = Document(html)
                summary_html = doc.summary()
                # Strip HTML tags from readability output
                clean = re.sub(r"<[^>]+>", " ", summary_html)
                clean = _html_lib.unescape(clean)
                clean = re.sub(r" {2,}", " ", clean)
                clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
                if len(clean) > len(body):
                    body = clean
                    logger.debug("readability succeeded for %s (%d chars)", url, len(body))
                # readability title is often cleaner than <title>
                rd_title = doc.title()
                if rd_title and rd_title != title:
                    title = rd_title
            except ImportError:
                logger.debug("readability-lxml not installed")
            except Exception as exc:
                logger.debug("readability failed for %s: %s", url, exc)

        # ── Layer 3: lxml XPath fallback ─────────────────────────────────────────
        if not body or len(body) < 100:
            fb = _extract_lxml_fallback(html, url)
            if len(fb) > len(body):
                body = fb
                logger.debug("lxml fallback used for %s (%d chars)", url, len(body))

    # ── Layer 4: camoufox-browser sidecar (HTTP, optional) ───────────────────────
    # POST to the camoufox-browser container; only runs when standard layers produced
    # < 200 chars and the user has enabled camoufox in settings.
    if not fetch_failed and camoufox_enabled and camoufox_url and len(body.strip()) < 200:
        try:
            logger.debug("calling camoufox-browser sidecar for %s", url)
            async with httpx.AsyncClient(timeout=camoufox_timeout + 10) as cf_client:
                cf_resp = await cf_client.post(
                    camoufox_url.rstrip("/") + "/fetch",
                    json={"url": url, "timeout": camoufox_timeout},
                )
            cf_data = cf_resp.json()
            if cf_data.get("status") == "ok":
                html_cf = cf_data.get("html", "")

                try:
                    import trafilatura
                    cf_body = trafilatura.extract(
                        html_cf,
                        url=url,
                        include_comments=False,
                        include_tables=True,
                        favor_recall=True,
                        output_format="markdown",
                    )
                    if cf_body and len(cf_body.strip()) > len(body):
                        body = cf_body.strip()
                        logger.debug("camoufox+trafilatura succeeded for %s (%d chars)", url, len(body))
                except Exception:
                    pass

                if len(body.strip()) < 200:
                    fb = _extract_lxml_fallback(html_cf, url)
                    if len(fb) > len(body):
                        body = fb
                        logger.debug("camoufox+lxml succeeded for %s (%d chars)", url, len(body))

                if html_cf:
                    cf_title, cf_desc, cf_img = _meta_extract(html_cf)
                    if cf_title and not title:
                        title = cf_title
                    if cf_desc and not excerpt:
                        excerpt = cf_desc
                    if cf_img and not img_url:
                        has_img = True
                        img_url = cf_img
            else:
                logger.warning("camoufox-browser error for %s: %s", url, cf_data.get("message"))
        except Exception as exc:
            logger.warning("camoufox-browser call failed for %s: %s", url, exc)

    partial = len(body.strip()) < 200

    if not excerpt and body:
        first = body.split("\n\n")[0].strip()
        if len(first) > 20:
            excerpt = first[:280]

    return {
        "title": title,
        "excerpt": excerpt,
        "body": body,
        "has_img": has_img,
        "img_url": img_url,
        "partial": partial,
    }


async def _suggest_tags(db: AsyncSession, title: str, excerpt: str, body: str, count: int = 3) -> list[str]:
    """Use LM Studio to suggest tags for an entry. Returns list of tag strings."""
    import logging
    from app.core.config import settings
    from app.services import config as config_svc

    logger = logging.getLogger(__name__)

    if count <= 0:
        return []

    base_url = await config_svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    if not base_url or not base_url.strip():
        return []

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            base_url=base_url.rstrip("/") + "/",
            api_key="not-needed",
            timeout=float(await config_svc.get_config_value(db, "llm_timeout", default=str(settings.llm_timeout))),
        )
        model = await config_svc.get_config_value(db, "llm_model", default=settings.llm_model)

        prompt = (
            f"Suggest exactly {count} concise tags for the following knowledge entry. "
            f"Tags should be single words or short phrases (1-2 words each). "
            f"Respond with ONLY the tags, one per line, no numbering, no extra text.\n\n"
            f"Title: {title}\n"
            f"Excerpt: {excerpt}\n"
            f"Body: {body[:800]}..."
        )

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=60,
        )
        raw_content = response.choices[0].message.content
        if not raw_content:
            return []

        tags = []
        for line in raw_content.split("\n"):
            tag = line.strip().lstrip("-").strip()
            if tag:
                tags.append(tag)
        return tags[:count]
    except Exception as exc:
        logger.warning("Tag suggestion failed: %s", exc)
        return []


async def suggest_topic(
    db: AsyncSession,
    title: str,
    excerpt: str,
    body: str,
    feedback: str | None = None,
) -> dict | None:
    """Use LM Studio to suggest a topic without creating it. Returns dict with name, description, color, is_new or None."""
    import logging
    import random
    import re
    from app.core.config import settings
    from app.services import config as config_svc
    from app.models.topic import Topic

    logger = logging.getLogger(__name__)

    base_url = await config_svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    if not base_url or not base_url.strip():
        return None

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            base_url=base_url.rstrip("/") + "/",
            api_key="not-needed",
            timeout=float(await config_svc.get_config_value(db, "llm_timeout", default=str(settings.llm_timeout))),
        )
        model = await config_svc.get_config_value(db, "llm_model", default=settings.llm_model)

        # Get existing topics
        topics_result = await db.execute(select(Topic).order_by(Topic.name))
        topics = topics_result.scalars().all()
        topic_list = ", ".join([f"{t.name}" for t in topics]) if topics else "none"

        feedback_text = f"\nUser feedback on previous suggestion: {feedback}\nPlease consider this feedback.\n" if feedback else ""

        prompt = (
            f"You are a knowledge organizer. Given a knowledge entry, classify it into one of these existing topics: {topic_list}\n\n"
            f"If none fit well, suggest a NEW topic with a concise name (2-4 words), a short one-sentence description, and a color from this list: "
            f"teal, green, red, purple, yellow, pink, orange, blue, brown, cyan, magenta, lime.\n\n"
            f"Title: {title}\n"
            f"Excerpt: {excerpt}\n"
            f"Body: {body[:800]}..."
            f"{feedback_text}\n\n"
            f"Respond in this exact format:\n"
            f"NAME: <topic name>\n"
            f"DESCRIPTION: <one sentence description>\n"
            f"COLOR: <color name>\n"
            f"IS_NEW: <yes or no>"
        )

        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=120,
        )
        raw_content = response.choices[0].message.content
        if not raw_content:
            logger.warning("LM Studio returned empty topic suggestion")
            return None

        # Parse response
        name_match = re.search(r"NAME:\s*(.+)", raw_content, re.IGNORECASE)
        desc_match = re.search(r"DESCRIPTION:\s*(.+)", raw_content, re.IGNORECASE)
        color_match = re.search(r"COLOR:\s*(.+)", raw_content, re.IGNORECASE)
        is_new_match = re.search(r"IS_NEW:\s*(yes|no)", raw_content, re.IGNORECASE)

        suggested_name = name_match.group(1).strip() if name_match else ""
        if not suggested_name:
            logger.warning("Could not parse topic name from LM Studio response")
            return None

        suggested_lower = suggested_name.lower()
        for t in topics:
            if t.name.lower() == suggested_lower:
                return {"name": t.name, "description": t.description or "", "color": t.color, "is_new": False}

        # New topic
        description = desc_match.group(1).strip() if desc_match else ""
        color_name = (color_match.group(1).strip() if color_match else "teal").lower()
        is_new = is_new_match.group(1).lower() == "yes" if is_new_match else True

        # Map color names to oklch values
        color_map = {
            "teal": "oklch(72% 0.08 200)", "green": "oklch(65% 0.10 160)", "red": "oklch(68% 0.07 30)",
            "purple": "oklch(60% 0.09 280)", "yellow": "oklch(74% 0.06 80)", "pink": "oklch(62% 0.11 320)",
            "orange": "oklch(70% 0.08 120)", "blue": "oklch(67% 0.09 240)", "brown": "oklch(75% 0.05 50)",
            "cyan": "oklch(63% 0.10 190)", "magenta": "oklch(71% 0.07 340)", "lime": "oklch(66% 0.08 100)",
        }
        color = color_map.get(color_name, random.choice(list(color_map.values())))

        return {"name": suggested_name, "description": description, "color": color, "is_new": is_new}
    except Exception as exc:
        logger.warning("Topic suggestion failed: %s", exc)
        return None


async def create_entry(
    db: AsyncSession,
    topic_id: str | None,
    entry_type: str,
    title: str,
    excerpt: str = "",
    body: str = "",
    source_url: str | None = None,
    source_label: str | None = None,
    has_img: bool = False,
    img_url: str | None = None,
    is_starred: bool = False,
    tag_names: list[str] | None = None,
    topic_suggestion: dict | None = None,
) -> ArticleDetailOut:
    from app.core.config import settings
    from app.services import config as config_svc

    # Auto-categorize if no topic provided (treat empty string as null)
    if not topic_id:
        if topic_suggestion:
            # Use user-approved suggestion
            from app.models.topic import Topic
            import re
            suggested_lower = topic_suggestion["name"].lower()
            topics_result = await db.execute(select(Topic).order_by(Topic.name))
            existing = None
            for t in topics_result.scalars().all():
                if t.name.lower() == suggested_lower:
                    existing = t
                    break
            if existing:
                topic_id = existing.id
            else:
                slug = re.sub(r'[^\w\s-]', '', suggested_lower).strip()
                slug = re.sub(r'[-\s]+', '-', slug)[:64]
                if not slug:
                    slug = "topic"
                base_slug = slug
                counter = 1
                while True:
                    existing_slug = await db.execute(select(Topic).where(Topic.slug == slug))
                    if existing_slug.scalar_one_or_none() is None:
                        break
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                new_topic = Topic(
                    id=str(uuid.uuid4()),
                    slug=slug,
                    name=topic_suggestion["name"],
                    color=topic_suggestion.get("color", _IMG_COLORS[0]),
                    description=topic_suggestion.get("description", ""),
                )
                db.add(new_topic)
                await db.flush()
                topic_id = new_topic.id
        else:
            topic_id, _ = await _classify_entry(db, title, excerpt, body)

    entry_id = str(uuid.uuid4())
    color = _IMG_COLORS[int(entry_id.replace("-", ""), 16) % len(_IMG_COLORS)]

    # Compute word count and read time
    word_count = len(body.split()) if body else 0
    read_time = max(1, round(word_count / 200))

    entry = Entry(
        id=entry_id,
        topic_id=topic_id,
        type=entry_type,
        title=title,
        excerpt=excerpt,
        body=body,
        word_count=word_count,
        read_time_min=read_time,
        has_img=has_img,
        img_url=img_url,
        img_color=color,
        is_starred=is_starred,
        source_url=source_url,
        source_label=source_label,
    )
    db.add(entry)
    await db.flush()

    # Merge user-provided tags with auto-suggested tags
    final_tags = list(tag_names or [])
    if not final_tags:
        try:
            auto_count = int(await config_svc.get_config_value(db, "auto_tag_count", default=str(settings.auto_tag_count)))
            if auto_count > 0:
                suggested = await _suggest_tags(db, title, excerpt, body, count=auto_count)
                final_tags = suggested
        except Exception:
            pass

    for tag_name in final_tags:
        tag_result = await db.execute(select(Tag).where(Tag.name == tag_name))
        tag = tag_result.scalar_one_or_none()
        if tag is None:
            tag = Tag(id=str(uuid.uuid4()), name=tag_name)
            db.add(tag)
            await db.flush()
        await db.execute(insert(entry_tags).values(entry_id=entry.id, tag_id=tag.id))

    await db.commit()
    await db.refresh(entry)

    return ArticleDetailOut(
        id=entry.id,
        topic_id=entry.topic_id,
        type=entry.type,
        title=entry.title,
        excerpt=entry.excerpt,
        body=entry.body,
        tags=final_tags,
        date=_format_date(entry.created_at),
        source=_entry_source(entry),
        source_url=entry.source_url,
        has_img=entry.has_img,
        img_url=entry.img_url,
        img_height=entry.img_height,
        img_color=entry.img_color,
        is_starred=entry.is_starred,
        word_count=entry.word_count,
        read_time_min=entry.read_time_min,
        backlink_count=0,
    )


async def add_attachment(
    db: AsyncSession,
    entry_id: str,
    filename: str,
    ext: str,
    size_bytes: int,
    storage_path: str,
) -> "AttachmentOut":
    from app.models.attachment import Attachment
    from app.schemas.attachment import AttachmentOut

    att = Attachment(
        id=str(uuid.uuid4()),
        entry_id=entry_id,
        filename=filename,
        ext=ext,
        size_bytes=size_bytes,
        storage_path=storage_path,
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return AttachmentOut(id=att.id, filename=att.filename, ext=att.ext, size_bytes=att.size_bytes, created_at=att.created_at)


async def remove_attachment(db: AsyncSession, attachment_id: str) -> str | None:
    """Delete attachment DB record; return storage_path so caller can remove the file."""
    from app.models.attachment import Attachment

    result = await db.execute(select(Attachment).where(Attachment.id == attachment_id))
    att = result.scalar_one_or_none()
    if att is None:
        return None
    path = att.storage_path
    await db.delete(att)
    await db.commit()
    return path


# ── Phase 5 additions ─────────────────────────────────────────────────────────

async def _sync_tags(db: AsyncSession, entry: Entry, tag_names: list[str]) -> None:
    """Replace the entry's tag associations with the given list (find-or-create tags)."""
    await db.execute(delete(entry_tags).where(entry_tags.c.entry_id == entry.id))
    for tag_name in tag_names:
        tag_result = await db.execute(select(Tag).where(Tag.name == tag_name))
        tag = tag_result.scalar_one_or_none()
        if tag is None:
            tag = Tag(id=str(uuid.uuid4()), name=tag_name)
            db.add(tag)
            await db.flush()
        await db.execute(insert(entry_tags).values(entry_id=entry.id, tag_id=tag.id))


async def detect_and_store_backlinks(db: AsyncSession, entry: Entry) -> None:
    """Scan entry body for [[Title]] and create backlink relations to matching entries."""
    titles = re.findall(r"\[\[(.+?)\]\]", entry.body or "")
    # Remove old auto-detected backlinks from this entry
    await db.execute(
        delete(Relation).where(Relation.from_entry_id == entry.id, Relation.kind == "backlink")
    )
    if not titles:
        return
    for title in set(titles):
        result = await db.execute(
            select(Entry).where(
                Entry.topic_id == entry.topic_id,
                func.lower(Entry.title) == title.lower(),
                Entry.id != entry.id,
            )
        )
        target = result.scalar_one_or_none()
        if target is not None:
            db.add(Relation(
                id=str(uuid.uuid4()),
                from_entry_id=entry.id,
                to_entry_id=target.id,
                kind="backlink",
            ))


async def update_entry(db: AsyncSession, entry_id: str, updates: "EntryUpdate") -> ArticleDetailOut | None:
    result = await db.execute(
        select(Entry).options(selectinload(Entry.tags)).where(Entry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return None

    if updates.title is not None:
        entry.title = updates.title
    if updates.type is not None:
        entry.type = updates.type
    if updates.body is not None:
        entry.body = updates.body
        entry.word_count = len(updates.body.split())
        entry.read_time_min = max(1, round(entry.word_count / 200))
    if updates.excerpt is not None:
        entry.excerpt = updates.excerpt
    if updates.source_url is not None:
        entry.source_url = updates.source_url
    if updates.source_label is not None:
        entry.source_label = updates.source_label
    if updates.is_starred is not None:
        entry.is_starred = updates.is_starred
    if updates.img_url is not None:
        entry.img_url = updates.img_url

    await db.flush()

    if updates.tags is not None:
        await _sync_tags(db, entry, updates.tags)

    await detect_and_store_backlinks(db, entry)
    await db.commit()
    await db.refresh(entry)

    # Fetch current tags after sync
    tag_result = await db.execute(
        select(Tag.name)
        .join(entry_tags, Tag.id == entry_tags.c.tag_id)
        .where(entry_tags.c.entry_id == entry.id)
    )
    tag_names = list(tag_result.scalars().all())

    bl_count = await _backlink_count(db, entry.id)
    return ArticleDetailOut(
        id=entry.id,
        topic_id=entry.topic_id,
        type=entry.type,
        title=entry.title,
        excerpt=entry.excerpt,
        body=entry.body,
        tags=tag_names,
        date=_format_date(entry.created_at),
        source=_entry_source(entry),
        source_url=entry.source_url,
        has_img=entry.has_img,
        img_url=entry.img_url,
        img_height=entry.img_height,
        img_color=entry.img_color,
        is_starred=entry.is_starred,
        word_count=entry.word_count,
        read_time_min=entry.read_time_min,
        backlink_count=bl_count,
    )


async def delete_entry(db: AsyncSession, entry_id: str) -> bool:
    result = await db.execute(select(Entry).where(Entry.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        return False
    await db.delete(entry)
    await db.commit()
    return True


async def suggest_related(db: AsyncSession, entry_id: str, limit: int = 5) -> list[RelatedEntryOut]:
    """Return entries in the same topic sharing ≥1 tag, sorted by overlap count."""
    # Get this entry's topic and tags
    result = await db.execute(
        select(Entry).options(selectinload(Entry.tags)).where(Entry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return []

    tag_ids_result = await db.execute(
        select(entry_tags.c.tag_id).where(entry_tags.c.entry_id == entry_id)
    )
    tag_ids = [r[0] for r in tag_ids_result]
    if not tag_ids:
        return []

    # Find existing relation targets (both directions)
    existing_result = await db.execute(
        select(Relation.to_entry_id).where(Relation.from_entry_id == entry_id)
    )
    existing_ids = {r[0] for r in existing_result} | {entry_id}

    # Count shared tags per candidate entry
    shared_count = func.count(entry_tags.c.tag_id).label("shared")
    stmt = (
        select(Entry, shared_count)
        .join(entry_tags, Entry.id == entry_tags.c.entry_id)
        .where(
            entry_tags.c.tag_id.in_(tag_ids),
            Entry.topic_id == entry.topic_id,
            Entry.id.notin_(existing_ids),
        )
        .group_by(Entry.id)
        .order_by(shared_count.desc())
        .limit(limit)
    )
    rows = await db.execute(stmt)

    return [
        RelatedEntryOut(id=e.id, relation_id="", title=e.title, type=e.type, img_color=e.img_color)
        for e, _ in rows
    ]
