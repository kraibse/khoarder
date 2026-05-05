from pydantic import BaseModel


class ConfigOut(BaseModel):
    llm_base_url: str
    llm_model: str
    llm_timeout: int
    llm_context_entries: int
    system_prompt: str
    auto_tag_count: int
    camoufox_enabled: bool
    camoufox_timeout: int
    camoufox_url: str
    suggest_searxng_url: str = ""
    suggest_use_llm_expand: bool = False
    suggest_use_llm_rerank: bool = False


class ConfigUpdate(BaseModel):
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_timeout: int | None = None
    llm_context_entries: int | None = None
    system_prompt: str | None = None
    auto_tag_count: int | None = None
    camoufox_enabled: bool | None = None
    camoufox_timeout: int | None = None
    camoufox_url: str | None = None
    suggest_searxng_url: str | None = None
    suggest_use_llm_expand: bool | None = None
    suggest_use_llm_rerank: bool | None = None


class HealthOut(BaseModel):
    reachable: bool
    model: str | None = None
    error: str | None = None


class CamoufoxStatusOut(BaseModel):
    installed: bool
    browser_ready: bool
    message: str = ""
