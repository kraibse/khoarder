from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import topics, entries, attachments, relations, qa, config, conversations
from app.db.session import get_db
from app.services.entries import list_all_tags

router = APIRouter(prefix="/api")
router.include_router(topics.router)
router.include_router(entries.router)
router.include_router(attachments.router)
router.include_router(relations.router)
router.include_router(qa.router)
router.include_router(config.router)
router.include_router(conversations.router)


@router.get("/tags", response_model=list[str], tags=["tags"])
async def list_tags(db: AsyncSession = Depends(get_db)):
    return await list_all_tags(db)
