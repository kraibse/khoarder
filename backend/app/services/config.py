from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config


async def get_config_value(db: AsyncSession, key: str, default: str = "") -> str:
    result = await db.execute(select(Config).where(Config.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def set_config_value(db: AsyncSession, key: str, value: str) -> Config:
    result = await db.execute(select(Config).where(Config.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        row = Config(key=key, value=value)
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
