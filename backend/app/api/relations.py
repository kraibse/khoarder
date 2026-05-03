from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.relation import RelationCreate, RelationOut
from app.services import relations as svc

router = APIRouter(prefix="/relations", tags=["relations"])


@router.post("", response_model=RelationOut, status_code=201)
async def create_relation(body: RelationCreate, db: AsyncSession = Depends(get_db)):
    return await svc.add_relation(db, body)


@router.delete("/{relation_id}", status_code=204)
async def delete_relation(relation_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await svc.remove_relation(db, relation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Relation not found")
