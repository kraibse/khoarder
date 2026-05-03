import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.relation import Relation
from app.schemas.relation import RelationCreate, RelationOut


async def add_relation(db: AsyncSession, data: RelationCreate) -> RelationOut:
    """Create a relation; silently skip if an identical one already exists."""
    existing = await db.execute(
        select(Relation).where(
            Relation.from_entry_id == data.from_entry_id,
            Relation.to_entry_id == data.to_entry_id,
            Relation.kind == data.kind,
        )
    )
    rel = existing.scalar_one_or_none()
    if rel is not None:
        return RelationOut(id=rel.id, from_entry_id=rel.from_entry_id,
                           to_entry_id=rel.to_entry_id, kind=rel.kind)

    rel = Relation(
        id=str(uuid.uuid4()),
        from_entry_id=data.from_entry_id,
        to_entry_id=data.to_entry_id,
        kind=data.kind,
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return RelationOut(id=rel.id, from_entry_id=rel.from_entry_id,
                       to_entry_id=rel.to_entry_id, kind=rel.kind)


async def remove_relation(db: AsyncSession, relation_id: str) -> bool:
    result = await db.execute(select(Relation).where(Relation.id == relation_id))
    rel = result.scalar_one_or_none()
    if rel is None:
        return False
    await db.delete(rel)
    await db.commit()
    return True
