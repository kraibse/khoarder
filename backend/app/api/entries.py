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
    EntryFromChatCreate,
    EntryOut,
    EntryUpdate,
    RelatedEntryOut,
    TopicPreviewRequest,
    TopicSuggestionOut,
    URLImportRequest,
    URLPreviewOut,
)
from app.schemas.attachment import AttachmentOut
from app.services import entries as svc
from app.services import attachments as file_svc
from app.services import config as config_svc

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
        topic_suggestion=body.topic_suggestion.model_dump() if body.topic_suggestion else None,
    )


async def _extractor_params(db: AsyncSession) -> dict:
    """Load browser extraction params from runtime config.

    Mirrors the persisted Config table so toggling Browserless/Camoufox in the
    Settings page takes effect on the next import without a restart.
    """
    def _bool(raw: str) -> bool:
        return raw.lower() in ("true", "1", "yes")

    cf_enabled = _bool(await config_svc.get_config_value(db, "camoufox_enabled", default="false"))
    cf_timeout = int(await config_svc.get_config_value(db, "camoufox_timeout", default=str(settings.camoufox_timeout)))
    cf_url = await config_svc.get_config_value(db, "camoufox_url", default=settings.camoufox_url)
    fs_url = await config_svc.get_config_value(db, "flaresolverr_url", default=settings.flaresolverr_url)

    bl_enabled = _bool(await config_svc.get_config_value(db, "browserless_enabled", default="false"))
    bl_token = await config_svc.get_config_value(db, "browserless_token", default=settings.browserless_token)
    bl_url = await config_svc.get_config_value(db, "browserless_url", default=settings.browserless_url)
    bl_timeout = int(await config_svc.get_config_value(db, "browserless_timeout", default=str(settings.browserless_timeout)))
    static_timeout = int(await config_svc.get_config_value(db, "static_fetch_timeout", default=str(settings.static_fetch_timeout)))

    return {
        "camoufox_enabled": cf_enabled,
        "camoufox_timeout": cf_timeout,
        "camoufox_url": cf_url,
        "flaresolverr_url": fs_url,
        "browserless_enabled": bl_enabled,
        "browserless_url": bl_url,
        "browserless_token": bl_token,
        "browserless_timeout": bl_timeout,
        "static_fetch_timeout": static_timeout,
    }


@router.post("/preview-import-url", response_model=URLPreviewOut)
async def preview_import_url(body: URLImportRequest, db: AsyncSession = Depends(get_db)):
    extracted = await svc.extract_url_content(body.url, **await _extractor_params(db), db=db)
    suggestion = None
    if not body.topic_id:
        suggestion = await svc.suggest_topic(
            db, extracted["title"], extracted["excerpt"], extracted["body"]
        )
    return URLPreviewOut(
        title=extracted["title"],
        excerpt=extracted["excerpt"],
        body=extracted["body"],
        has_img=extracted["has_img"],
        img_url=extracted["img_url"],
        suggestion=TopicSuggestionOut(**suggestion) if suggestion else None,
        partial=extracted.get("partial", False),
        failure_reason=extracted.get("failure_reason"),
        diagnostics=extracted.get("diagnostics"),
    )


@router.post("/import-url", response_model=ArticleDetailOut, status_code=201)
async def import_url(body: URLImportRequest, db: AsyncSession = Depends(get_db)):
    extracted = await svc.extract_url_content(body.url, **await _extractor_params(db), db=db)
    entry_type = "Article" if len(extracted["body"]) > 200 else "Reference"

    from app.services.imports.fast_paths import arxiv_id, arxiv_pdf_url

    is_arxiv = arxiv_id(body.url) is not None
    if is_arxiv:
        entry_type = "Paper"

    entry = await svc.create_entry(
        db,
        topic_id=body.topic_id,
        entry_type=entry_type,
        title=extracted["title"],
        excerpt=extracted["excerpt"],
        body=extracted["body"],
        source_url=body.url,
        source_label=None,
        has_img=extracted["has_img"],
        img_url=extracted["img_url"],
        tag_names=[],
        topic_suggestion=body.topic_suggestion.model_dump() if body.topic_suggestion else None,
    )

    if is_arxiv:
        paper_id = arxiv_id(body.url)
        if paper_id:
            try:
                pdf_url = arxiv_pdf_url(paper_id)
                filename = f"{paper_id}.pdf"
                async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                    resp = await client.get(pdf_url)
                    if resp.status_code == 200:
                        import uuid as _uuid
                        attachment_id = str(_uuid.uuid4())
                        rel_path = file_svc.storage_path_for(entry.id, attachment_id, filename)
                        abs_p = file_svc.abs_path(rel_path)
                        abs_p.parent.mkdir(parents=True, exist_ok=True)
                        abs_p.write_bytes(resp.content)
                        await svc.add_attachment(
                            db,
                            entry_id=entry.id,
                            filename=filename,
                            ext="pdf",
                            size_bytes=len(resp.content),
                            storage_path=rel_path,
                        )
            except Exception:
                pass

    return entry


@router.post("/{entry_id}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_attachment(
    entry_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    ext = pathlib.Path(file.filename or "file").suffix.lstrip(".").lower()
    filename = pathlib.Path(file.filename or "file").name
    storage_path = f"{settings.storage_path}/uploads/{entry_id}"
    pathlib.Path(storage_path).mkdir(parents=True, exist_ok=True)
    target = f"{storage_path}/{filename}"
    content = await file.read()
    with open(target, "wb") as f:
        f.write(content)
    return await file_svc.add_attachment(
        db,
        entry_id=entry_id,
        filename=filename,
        ext=ext,
        size_bytes=len(content),
        storage_path=target,
    )


@router.post("/from-chat", response_model=ArticleDetailOut, status_code=201)
async def create_entry_from_chat(body: EntryFromChatCreate, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.create_entry_from_chat(
            db,
            message_id=body.message_id,
            conversation_id=body.conversation_id,
            entry_type=body.type,
            title=body.title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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


@router.post("/preview-topic", response_model=TopicSuggestionOut)
async def preview_topic(body: TopicPreviewRequest, db: AsyncSession = Depends(get_db)):
    result = await svc.suggest_topic(db, body.title, body.excerpt, body.body, body.feedback)
    if result is None:
        raise HTTPException(status_code=503, detail="Topic suggestion unavailable — check LM Studio connection")
    return TopicSuggestionOut(**result)


@router.get("/{entry_id}/suggestions", response_model=list[RelatedEntryOut])
async def get_suggestions(entry_id: str, db: AsyncSession = Depends(get_db)):
    return await svc.suggest_related(db, entry_id)


@router.post("/{entry_id}/suggest-related", response_model=list[dict])
async def suggest_related_entries(entry_id: str, db: AsyncSession = Depends(get_db)):
    from app.services import overview as overview_svc
    try:
        return await overview_svc.suggest_related(db, entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
