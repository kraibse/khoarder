import pathlib

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.entry import (
    ArticleDetailOut,
    BacklinkOut,
    EntryCreate,
    EntryOut,
    EntryUpdate,
    RelatedEntryOut,
    URLImportRequest,
)
from app.schemas.attachment import AttachmentOut
from app.services import entries as svc
from app.services import attachments as file_svc

router = APIRouter(prefix="/entries", tags=["entries"])


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[EntryOut])
async def list_entries(
    topic_id: str | None = Query(None),
    type: str | None = Query(None),
    sort: str = Query("date_desc"),
    q: str | None = Query(None),
    tag: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.list_entries(db, topic_id=topic_id, entry_type=type, sort=sort, q=q, tag=tag)


@router.get("/{entry_id}", response_model=ArticleDetailOut)
async def get_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    entry = await svc.get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.get("/{entry_id}/backlinks", response_model=list[BacklinkOut])
async def get_backlinks(entry_id: str, db: AsyncSession = Depends(get_db)):
    return await svc.get_backlinks(db, entry_id)


@router.get("/{entry_id}/related", response_model=list[RelatedEntryOut])
async def get_related(entry_id: str, db: AsyncSession = Depends(get_db)):
    return await svc.get_related(db, entry_id)


@router.get("/{entry_id}/attachments", response_model=list[AttachmentOut])
async def get_attachments(entry_id: str, db: AsyncSession = Depends(get_db)):
    return await svc.get_attachments(db, entry_id)


# ── Write ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=ArticleDetailOut, status_code=201)
async def create_entry(body: EntryCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_entry(
        db,
        topic_id=body.topic_id,
        entry_type=body.type,
        title=body.title,
        excerpt=body.excerpt,
        body=body.body,
        source_url=body.source_url,
        source_label=body.source_label,
        has_img=body.has_img,
        img_url=body.img_url,
        is_starred=body.is_starred,
        tag_names=body.tags,
    )


@router.post("/import-url", response_model=ArticleDetailOut, status_code=201)
async def import_url(body: URLImportRequest, db: AsyncSession = Depends(get_db)):
    import re
    from html.parser import HTMLParser
    from urllib.parse import urlparse

    title = body.url
    excerpt = ""
    article_body = ""
    has_img = False
    img_height = 200

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.get(body.url, headers={"User-Agent": "KnowledgeHoarder/1.0"})
            resp.raise_for_status()
            html = resp.text

        # Extract <title>
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if m:
            title = m.group(1).strip()

        # Extract <meta name="description">
        m = re.search(
            r'<meta\s[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        if not m:
            m = re.search(
                r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']description["\']',
                html, re.IGNORECASE
            )
        if m:
            excerpt = m.group(1).strip()

        # Extract og:image
        img_url = None
        m = re.search(
            r'<meta\s[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            html, re.IGNORECASE
        )
        if not m:
            m = re.search(
                r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
                html, re.IGNORECASE
            )
        if m:
            has_img = True
            img_url = m.group(1).strip()

        # Extract body text from paragraphs
        is_wikipedia = "wikipedia.org" in body.url or "wikimedia.org" in body.url

        # Simple HTML tag stripper
        class TagStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text_parts: list[str] = []
                self.skip = 0
                self.in_paragraph = False
                self.in_heading = False
                self.heading_level = 0

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag in ("script", "style", "nav", "footer", "header", "aside"):
                    self.skip += 1
                elif tag == "p":
                    self.in_paragraph = True
                    # For Wikipedia, skip reference paragraphs
                    if is_wikipedia:
                        class_attr = attrs_dict.get("class", "")
                        if any(c in class_attr for c in ("reference", "navbox", "infobox", "mw-empty-elt")):
                            self.in_paragraph = False
                elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    self.in_heading = True
                    self.heading_level = int(tag[1])
                elif tag in ("br", "div"):
                    self.text_parts.append("\n")

            def handle_endtag(self, tag):
                if tag in ("script", "style", "nav", "footer", "header", "aside"):
                    self.skip -= 1
                elif tag == "p":
                    if self.in_paragraph and self.skip == 0:
                        self.text_parts.append("\n\n")
                    self.in_paragraph = False
                elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    if self.in_heading and self.skip == 0:
                        self.text_parts.append("\n\n")
                    self.in_heading = False
                    self.heading_level = 0

            def handle_data(self, data):
                if self.skip != 0:
                    return
                if self.in_heading:
                    prefix = "#" * self.heading_level + " "
                    # Only add prefix at the start of a heading block
                    if not self.text_parts or self.text_parts[-1].endswith("\n"):
                        self.text_parts.append(prefix + data)
                    else:
                        self.text_parts.append(data)
                elif self.in_paragraph:
                    self.text_parts.append(data)

            def get_text(self) -> str:
                return re.sub(r"\n\s*\n", "\n\n", "".join(self.text_parts)).strip()

        stripper = TagStripper()
        # Feed only a relevant portion for performance
        feed = html
        if is_wikipedia:
            # Try to isolate the main content area
            content_match = re.search(
                r'<div[^>]*id=["\']mw-content-text["\'][^>]*>(.*?)</div>\s*(?:<div[^>]*class=["\']catlinks["\']|<div[^>]*id=["\']mw-data-after-content["\']|</body>)',
                html, re.IGNORECASE | re.DOTALL
            )
            if content_match:
                feed = content_match.group(1)

        stripper.feed(feed)
        article_body = stripper.get_text()

        # If generic extraction yielded little, try broader extraction
        if len(article_body) < 100 and not is_wikipedia:
            # Fallback: grab all paragraphs
            paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.IGNORECASE | re.DOTALL)
            cleaned = []
            for p in paragraphs:
                # Strip inner tags
                txt = re.sub(r"<[^>]+>", "", p)
                txt = re.sub(r"\s+", " ", txt).strip()
                if len(txt) > 40:
                    cleaned.append(txt)
            article_body = "\n\n".join(cleaned)

    except Exception:
        # Fallback: use hostname as title
        title = urlparse(body.url).hostname or body.url

    # Determine entry type based on content richness
    entry_type = "Article" if len(article_body) > 200 else "Reference"

    # Build body as simple markdown (paragraphs separated by blank lines)
    body_md = article_body

    # If we have a substantial body but no excerpt, use first paragraph as excerpt
    if not excerpt and body_md:
        first_para = body_md.split("\n\n")[0].strip()
        if len(first_para) > 20:
            excerpt = first_para[:280]

    return await svc.create_entry(
        db,
        topic_id=body.topic_id,
        entry_type=entry_type,
        title=title,
        excerpt=excerpt,
        body=body_md,
        source_url=body.url,
        source_label=None,
        has_img=has_img,
        img_url=img_url,
        tag_names=[],
    )


@router.post("/{entry_id}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    entry_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Verify entry exists
    entry = await svc.get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")

    import uuid
    attachment_id = str(uuid.uuid4())
    filename = file.filename or "upload"
    ext = pathlib.Path(filename).suffix.lstrip(".").lower() or "bin"

    try:
        storage_path, size_bytes = await file_svc.save_file(entry_id, attachment_id, file)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc))

    return await svc.add_attachment(
        db,
        entry_id=entry_id,
        filename=filename,
        ext=ext,
        size_bytes=size_bytes,
        storage_path=storage_path,
    )


@router.patch("/{entry_id}", response_model=ArticleDetailOut)
async def update_entry(entry_id: str, body: EntryUpdate, db: AsyncSession = Depends(get_db)):
    result = await svc.update_entry(db, entry_id, body)
    if result is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    return result


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(entry_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await svc.delete_entry(db, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")


@router.get("/{entry_id}/suggestions", response_model=list[RelatedEntryOut])
async def get_suggestions(entry_id: str, db: AsyncSession = Depends(get_db)):
    return await svc.suggest_related(db, entry_id)
