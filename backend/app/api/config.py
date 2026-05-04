import os

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.config import CamoufoxStatusOut, ConfigOut, ConfigUpdate, HealthOut
from app.services import config as svc

router = APIRouter(prefix="/config", tags=["config"])


# (key, python_type) — drives both _load_config and _save_config
_CONFIG_KEYS: list[tuple[str, type]] = [
    ("llm_base_url", str),
    ("llm_model", str),
    ("llm_timeout", int),
    ("llm_context_entries", int),
    ("system_prompt", str),
    ("auto_tag_count", int),
    ("camoufox_enabled", bool),
    ("camoufox_timeout", int),
    ("camoufox_headless", bool),
]


def _to_str(value: object, typ: type) -> str:
    if typ is bool:
        return "true" if value else "false"
    return str(value)


def _from_str(raw: str, typ: type) -> object:
    if typ is int:
        try:
            return int(raw)
        except (ValueError, TypeError):
            return 0
    if typ is bool:
        return raw.strip().lower() in ("true", "1", "yes")
    return raw


async def _load_config(db: AsyncSession) -> ConfigOut:
    values: dict[str, object] = {}
    for key, typ in _CONFIG_KEYS:
        default = getattr(settings, key)
        raw = await svc.get_config_value(db, key, default=_to_str(default, typ))
        values[key] = _from_str(raw, typ)
    return ConfigOut(**values)  # type: ignore[arg-type]


async def _save_config(db: AsyncSession, body: ConfigUpdate) -> ConfigOut:
    for key, typ in _CONFIG_KEYS:
        val = getattr(body, key, None)
        if val is not None:
            await svc.set_config_value(db, key, _to_str(val, typ))
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


@router.get("/camoufox-status", response_model=CamoufoxStatusOut)
async def camoufox_status():
    """Check whether the camoufox package and its browser binary are available."""
    try:
        import camoufox  # noqa: F401
    except ImportError:
        return CamoufoxStatusOut(
            installed=False,
            browser_ready=False,
            message="Package not installed. Run: pip install camoufox",
        )

    # Probe the browser binary path via camoufox's internal helper (API varies by version).
    try:
        from camoufox.pkgman import get_path  # type: ignore[import]
        path = str(get_path() or "")
        ready = bool(path) and os.path.exists(path)
    except Exception:
        ready = False

    if ready:
        return CamoufoxStatusOut(installed=True, browser_ready=True)
    return CamoufoxStatusOut(
        installed=True,
        browser_ready=False,
        message="Browser binary not downloaded. Run: python -m camoufox fetch",
    )
