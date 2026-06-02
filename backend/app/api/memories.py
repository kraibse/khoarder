from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.memory import MemoryCreate, MemoryUpdate, MemoryOut
from app.services import memory as memory_svc

router = APIRouter(prefix="/memories", tags=["memories"])


@router.post("", response_model=MemoryOut, status_code=201)
async def create_memory(body: MemoryCreate, db: AsyncSession = Depends(get_db)):
    return await memory_svc.create_memory(
        db,
        content=body.content,
        topic_id=body.topic_id,
        type=body.type,
        trust_score=body.trust_score,
    )


@router.get("", response_model=list[MemoryOut])
async def list_memories(topic_id: str | None = None, db: AsyncSession = Depends(get_db)):
    if topic_id is not None:
        return await memory_svc.list_memories(db, topic_id=topic_id)
    return await memory_svc.list_all_memories(db)


@router.get("/{memory_id}", response_model=MemoryOut)
async def get_memory(memory_id: str, db: AsyncSession = Depends(get_db)):
    mem = await memory_svc.get_memory(db, memory_id)
    if mem is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return MemoryOut.model_validate(mem)


@router.patch("/{memory_id}", response_model=MemoryOut)
async def update_memory(
    memory_id: str,
    body: MemoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await memory_svc.update_memory(
            db,
            memory_id=memory_id,
            content=body.content,
            type=body.type,
            trust_score=body.trust_score,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Memory not found")


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(memory_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await memory_svc.delete_memory(db, memory_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Memory not found")
