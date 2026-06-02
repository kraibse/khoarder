from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.schemas.memory import MemoryOut


async def create_memory(
    db: AsyncSession,
    content: str,
    topic_id: str | None = None,
    type: str = "fact",
    trust_score: float = 1.0,
) -> MemoryOut:
    mem = Memory(topic_id=topic_id, content=content, type=type, trust_score=trust_score)
    db.add(mem)
    await db.commit()
    await db.refresh(mem)
    return MemoryOut.model_validate(mem)


async def get_memory(db: AsyncSession, memory_id: str) -> Memory | None:
    result = await db.execute(select(Memory).where(Memory.id == memory_id))
    return result.scalar_one_or_none()


async def list_memories(db: AsyncSession, topic_id: str | None = None, limit: int = 100) -> list[MemoryOut]:
    stmt = select(Memory).order_by(Memory.updated_at.desc())
    if topic_id:
        stmt = stmt.where(Memory.topic_id == topic_id)
    else:
        stmt = stmt.where(Memory.topic_id.is_(None))
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return [MemoryOut.model_validate(m) for m in result.scalars().all()]


async def list_all_memories(db: AsyncSession, limit: int = 200) -> list[MemoryOut]:
    stmt = select(Memory).order_by(Memory.updated_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return [MemoryOut.model_validate(m) for m in result.scalars().all()]


async def recall_memories(
    db: AsyncSession,
    topic_id: str | None,
    query: str,
    limit_per_scope: int = 3,
) -> list[MemoryOut]:
    from app.services import search as search_svc

    memories: list[Memory] = []

    if topic_id:
        topic_stmt = select(Memory).where(Memory.topic_id == topic_id)
        result = await db.execute(topic_stmt)
        topic_mems = list(result.scalars().all())
        # heuristic: word overlap weighted by trust_score
        query_words = set(query.lower().split())
        topic_mems.sort(
            key=lambda m: len(set(m.content.lower().split()) & query_words) * m.trust_score,
            reverse=True,
        )
        memories.extend(topic_mems[:limit_per_scope])

    global_stmt = select(Memory).where(Memory.topic_id.is_(None))
    result = await db.execute(global_stmt)
    global_mems = list(result.scalars().all())
    query_words = set(query.lower().split())
    global_mems.sort(
        key=lambda m: len(set(m.content.lower().split()) & query_words) * m.trust_score,
        reverse=True,
    )
    memories.extend(global_mems[:limit_per_scope])

    return [MemoryOut.model_validate(m) for m in memories]


async def update_memory(
    db: AsyncSession,
    memory_id: str,
    content: str | None = None,
    type: str | None = None,
    trust_score: float | None = None,
) -> MemoryOut:
    mem = await get_memory(db, memory_id)
    if mem is None:
        raise ValueError("Memory not found")
    if content is not None:
        mem.content = content
    if type is not None:
        mem.type = type
    if trust_score is not None:
        mem.trust_score = trust_score
    await db.commit()
    await db.refresh(mem)
    return MemoryOut.model_validate(mem)


async def delete_memory(db: AsyncSession, memory_id: str) -> None:
    mem = await get_memory(db, memory_id)
    if mem is None:
        raise ValueError("Memory not found")
    await db.delete(mem)
    await db.commit()
