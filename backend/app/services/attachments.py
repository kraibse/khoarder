"""File I/O for attachment upload/download/delete."""
from __future__ import annotations

import pathlib
import uuid

import aiofiles
import aiofiles.os
from fastapi import UploadFile

from app.core.config import settings


def _uploads_dir(entry_id: str) -> pathlib.Path:
    return pathlib.Path(settings.storage_path) / "uploads" / entry_id


def storage_path_for(entry_id: str, attachment_id: str, filename: str) -> str:
    """Return relative path (relative to STORAGE_PATH) for a new attachment file."""
    safe = pathlib.Path(filename).name  # strip any directory traversal
    return f"uploads/{entry_id}/{attachment_id}_{safe}"


def abs_path(relative: str) -> pathlib.Path:
    return pathlib.Path(settings.storage_path) / relative


async def save_file(entry_id: str, attachment_id: str, upload: UploadFile) -> tuple[str, int]:
    """
    Write UploadFile to disk.
    Returns (relative_storage_path, size_bytes).
    Raises ValueError if file exceeds max_upload_bytes.
    """
    dest_dir = _uploads_dir(entry_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    rel = storage_path_for(entry_id, attachment_id, upload.filename or "file")
    dest = abs_path(rel)

    size = 0
    async with aiofiles.open(dest, "wb") as out:
        while chunk := await upload.read(256 * 1024):
            size += len(chunk)
            if size > settings.max_upload_bytes:
                await aiofiles.os.remove(dest)
                raise ValueError(
                    f"File exceeds maximum size of {settings.max_upload_bytes // (1024 * 1024)} MB"
                )
            await out.write(chunk)

    return rel, size


async def delete_file(storage_path: str) -> None:
    """Remove a stored file, silently ignore if already gone."""
    p = abs_path(storage_path)
    try:
        await aiofiles.os.remove(p)
    except FileNotFoundError:
        pass
