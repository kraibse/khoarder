import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.config import BrowserlessStatusOut, CamoufoxStatusOut, ConfigOut, ConfigUpdate, HealthOut, ModelsOut, LoadModelRequest
from app.services import config as svc

router = APIRouter(prefix="/config", tags=["config"])


# Standard keys that round-trip plainly between DB and ConfigOut/ConfigUpdate.
# `browserless_token` is intentionally absent — handled separately as write-only.
_CONFIG_KEYS: list[tuple[str, type]] = [
    ("llm_base_url", str),
    ("llm_model", str),
    ("llm_timeout", int),
    ("llm_context_entries", int),
    ("system_prompt", str),
    ("auto_tag_count", int),
    ("camoufox_enabled", bool),
    ("camoufox_timeout", int),
    ("camoufox_url", str),
    ("flaresolverr_url", str),
    ("browserless_enabled", bool),
    ("browserless_url", str),
    ("browserless_timeout", int),
    ("static_fetch_timeout", int),
    ("suggest_searxng_url", str),
    ("suggest_use_llm_expand", bool),
    ("suggest_use_llm_rerank", bool),
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
    token = await svc.get_config_value(db, "browserless_token", default=settings.browserless_token)
    values["browserless_token_set"] = bool(token.strip())
    return ConfigOut(**values)  # type: ignore[arg-type]


async def _save_config(db: AsyncSession, body: ConfigUpdate) -> ConfigOut:
    for key, typ in _CONFIG_KEYS:
        val = getattr(body, key, None)
        if val is not None:
            await svc.set_config_value(db, key, _to_str(val, typ))
            setattr(settings, key, val)
    if body.browserless_token is not None:
        await svc.set_config_value(db, "browserless_token", body.browserless_token)
        settings.browserless_token = body.browserless_token
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
    configured_model = await svc.get_config_value(db, "llm_model", default=settings.llm_model)
    if not base_url.strip():
        return HealthOut(
            reachable=False,
            configured_model=configured_model,
            error="LLM Studio is not configured. Set the base URL in Settings.",
        )
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(base_url.rstrip("/") + "/models")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                loaded_model = models[0].get("id") if models else None
                return HealthOut(
                    reachable=True,
                    model=loaded_model or configured_model,
                    configured_model=configured_model,
                )
            return HealthOut(
                reachable=False,
                configured_model=configured_model,
                error=f"LM Studio returned status {resp.status_code}",
            )
    except Exception as exc:
        return HealthOut(reachable=False, configured_model=configured_model, error=str(exc))


@router.get("/models", response_model=ModelsOut)
async def list_models(db: AsyncSession = Depends(get_db)):
    base_url = await svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    if not base_url.strip():
        return ModelsOut(models=[], error="LLM Studio is not configured.")
    mgmt_base = base_url.rstrip("/")
    if mgmt_base.endswith("/v1"):
        mgmt_base = mgmt_base[:-3]
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            # Try LM Studio management API first for richer info
            try:
                mgmt_resp = await client.get(mgmt_base + "/api/v0/models")
                if mgmt_resp.status_code == 200:
                    data = mgmt_resp.json()
                    models = data.get("data", [])
                    return ModelsOut(
                        models=[
                            ModelInfo(id=m.get("id", m.get("path", "unknown")), loaded=m.get("loaded", False))
                            for m in models
                        ]
                    )
            except Exception:
                pass
            # Fallback to OpenAI-compatible endpoint
            resp = await client.get(base_url.rstrip("/") + "/models")
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("data", [])
                return ModelsOut(
                    models=[ModelInfo(id=m.get("id", "unknown"), loaded=True) for m in models]
                )
            return ModelsOut(models=[], error=f"HTTP {resp.status_code}")
    except Exception as exc:
        return ModelsOut(models=[], error=str(exc))


@router.post("/load-model", status_code=202)
async def load_model(body: LoadModelRequest, db: AsyncSession = Depends(get_db)):
    base_url = await svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    if not base_url.strip():
        raise HTTPException(status_code=503, detail="LLM Studio is not configured.")
    mgmt_base = base_url.rstrip("/")
    if mgmt_base.endswith("/v1"):
        mgmt_base = mgmt_base[:-3]
    try:
        import httpx
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                mgmt_base + "/api/v0/models/load",
                json={"model": body.model},
            )
            if resp.status_code in (200, 202):
                return {"status": "loading", "model": body.model}
            raise HTTPException(status_code=resp.status_code, detail=resp.text[:200])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/camoufox-status", response_model=CamoufoxStatusOut)
async def camoufox_status(db: AsyncSession = Depends(get_db)):
    """Ping the camoufox-browser sidecar service and report its status."""
    url = await svc.get_config_value(db, "camoufox_url", default=settings.camoufox_url)
    if not url.strip():
        return CamoufoxStatusOut(
            installed=False,
            browser_ready=False,
            message="No service URL configured.",
        )
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url.rstrip("/") + "/health")
        if resp.status_code == 200:
            return CamoufoxStatusOut(installed=True, browser_ready=True)
        return CamoufoxStatusOut(
            installed=True,
            browser_ready=False,
            message=f"Service returned HTTP {resp.status_code}.",
        )
    except Exception as exc:
        return CamoufoxStatusOut(
            installed=False,
            browser_ready=False,
            message=f"Unreachable: {exc}",
        )


@router.get("/browserless-status", response_model=BrowserlessStatusOut)
async def browserless_status(db: AsyncSession = Depends(get_db)):
    """Ping Browserless with the configured token. Probes management endpoints
    that don't consume render units. Walks a small list because the cloud and
    self-hosted builds expose slightly different routes."""
    token = await svc.get_config_value(db, "browserless_token", default=settings.browserless_token)
    base = (await svc.get_config_value(db, "browserless_url", default=settings.browserless_url)).rstrip("/")
    if not token.strip():
        return BrowserlessStatusOut(configured=False, reachable=False, message="No API token configured.")

    probes = ("/sessions", "/pressure", "/json/version", "/")
    last_status: int | None = None
    last_body: str = ""
    last_path: str = ""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            for path in probes:
                try:
                    resp = await client.get(base + path, params={"token": token})
                except Exception as exc:
                    return BrowserlessStatusOut(configured=True, reachable=False, message=f"Unreachable: {exc}")
                if resp.status_code == 200:
                    return BrowserlessStatusOut(configured=True, reachable=True)
                if resp.status_code in (401, 403):
                    return BrowserlessStatusOut(configured=True, reachable=False, message="Token rejected.")
                last_status = resp.status_code
                last_body = resp.text[:160].strip().replace("\n", " ")
                last_path = path
    except Exception as exc:
        return BrowserlessStatusOut(configured=True, reachable=False, message=f"Unreachable: {exc}")

    detail = f"HTTP {last_status} on {last_path}"
    if last_body:
        detail += f" — {last_body}"
    return BrowserlessStatusOut(configured=True, reachable=False, message=detail)


@router.get("/flaresolverr-status", response_model=CamoufoxStatusOut)
async def flaresolverr_status(db: AsyncSession = Depends(get_db)):
    """Ping the FlareSolverr sidecar service and report its status."""
    url = await svc.get_config_value(db, "flaresolverr_url", default=settings.flaresolverr_url)
    if not url.strip():
        return CamoufoxStatusOut(
            installed=False,
            browser_ready=False,
            message="No service URL configured.",
        )
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url.rstrip("/") + "/")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "ok":
                return CamoufoxStatusOut(installed=True, browser_ready=True)
            return CamoufoxStatusOut(
                installed=True,
                browser_ready=False,
                message=f"Service status: {data.get('status')}",
            )
        return CamoufoxStatusOut(
            installed=True,
            browser_ready=False,
            message=f"Service returned HTTP {resp.status_code}.",
        )
    except Exception as exc:
        return CamoufoxStatusOut(
            installed=False,
            browser_ready=False,
            message=f"Unreachable: {exc}",
        )
