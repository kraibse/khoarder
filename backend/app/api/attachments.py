import mimetypes
import pathlib

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.attachment import Attachment
from app.services import attachments as file_svc
from app.services.entries import remove_attachment

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.get("/{attachment_id}/download")
async def download_attachment(attachment_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Attachment).where(Attachment.id == attachment_id))
    att = result.scalar_one_or_none()
    if att is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    abs_p = file_svc.abs_path(att.storage_path)
    if not abs_p.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    media_type = mimetypes.guess_type(att.filename)[0] or "application/octet-stream"
    return FileResponse(
        path=str(abs_p),
        media_type=media_type,
        filename=att.filename,
    )


@router.get("/{attachment_id}/view")
async def view_attachment(attachment_id: str, db: AsyncSession = Depends(get_db)):
    """Serve attachment inline (no forced download) for browser-native rendering."""
    result = await db.execute(select(Attachment).where(Attachment.id == attachment_id))
    att = result.scalar_one_or_none()
    if att is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    abs_p = file_svc.abs_path(att.storage_path)
    if not abs_p.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    media_type = mimetypes.guess_type(att.filename)[0] or "application/octet-stream"
    return FileResponse(
        path=str(abs_p),
        media_type=media_type,
        content_disposition_type="inline",
    )


@router.delete("/{attachment_id}", status_code=204)
async def delete_attachment(attachment_id: str, db: AsyncSession = Depends(get_db)):
    storage_path = await remove_attachment(db, attachment_id)
    if storage_path is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    await file_svc.delete_file(storage_path)
