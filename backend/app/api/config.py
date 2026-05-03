from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.config import ConfigOut, ConfigUpdate, HealthOut
from app.services import config as svc

router = APIRouter(prefix="/config", tags=["config"])


_CONFIG_KEYS = [
    ("llm_base_url", str),
    ("llm_model", str),
    ("llm_timeout", int),
    ("llm_context_entries", int),
    ("system_prompt", str),
    ("auto_tag_count", int),
]


async def _load_config(db: AsyncSession) -> ConfigOut:
    values = {}
    for key, typ in _CONFIG_KEYS:
        default = getattr(settings, key, "" if typ is str else 0)
        raw = await svc.get_config_value(db, key, default=str(default))
        values[key] = typ(raw) if typ is int else raw
    return ConfigOut(**values)


async def _save_config(db: AsyncSession, body: ConfigUpdate) -> ConfigOut:
    for key, typ in _CONFIG_KEYS:
        val = getattr(body, key, None)
        if val is not None:
            await svc.set_config_value(db, key, str(val))
            setattr(settings, key, val)
    return await _load_config(db)


@router.get("", response_model=ConfigOut)
async def get_config(db: AsyncSession = Depends(get_db)):
    return await _load_config(db)


@router.put("", response_model=ConfigOut)
async def update_config(body: ConfigUpdate, db: AsyncSession = Depends(get_db)):
    return await _save_config(db, body)


@router.get("/health", response_model=HealthOut)
async def health_check(db: AsyncSession = Depends(get_db)):
    base_url = await svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    model = await svc.get_config_value(db, "llm_model", default=settings.llm_model)
    if not base_url.strip():
        return HealthOut(reachable=False, error="LLM Studio is not configured. Set the base URL in Settings.")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(base_url.rstrip("/") + "/models")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                model_name = models[0].get("id") if models else None
                return HealthOut(reachable=True, model=model_name or model)
            return HealthOut(reachable=False, error=f"LM Studio returned status {resp.status_code}")
    except Exception as exc:
        return HealthOut(reachable=False, error=str(exc))
