import json
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.topic import TopicCreate, TopicOut, TopicUpdate
from app.services import topics as svc
from app.services.export_import import export_topic_json, import_topic_json

router = APIRouter(prefix="/topics", tags=["topics"])


@router.post("", response_model=TopicOut, status_code=201)
async def create_topic(body: TopicCreate, db: AsyncSession = Depends(get_db)):
    return await svc.create_topic(db, body)


@router.get("", response_model=list[TopicOut])
async def list_topics(db: AsyncSession = Depends(get_db)):
    return await svc.list_topics(db)


@router.get("/{slug_or_id}", response_model=TopicOut)
async def get_topic(slug_or_id: str, db: AsyncSession = Depends(get_db)):
    topic = await svc.get_topic(db, slug_or_id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.patch("/{slug_or_id}", response_model=TopicOut)
async def update_topic(slug_or_id: str, body: TopicUpdate, db: AsyncSession = Depends(get_db)):
    topic = await svc.update_topic(db, slug_or_id, body)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.get("/{slug_or_id}/tags", response_model=list[str])
async def get_topic_tags(slug_or_id: str, db: AsyncSession = Depends(get_db)):
    return await svc.get_topic_tags(db, slug_or_id)


@router.get("/{slug_or_id}/export")
async def export_topic(slug_or_id: str, db: AsyncSession = Depends(get_db)):
    data = await export_topic_json(db, slug_or_id)
    if not data:
        raise HTTPException(status_code=404, detail="Topic not found")

    slug = data["topic"]["slug"]
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{slug}-{date_str}.json"

    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{slug_or_id}/import", status_code=200)
async def import_topic(
    slug_or_id: str,
    data: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await import_topic_json(db, slug_or_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result
