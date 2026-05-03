from pydantic import BaseModel


class ConfigOut(BaseModel):
    llm_base_url: str
    llm_model: str
    llm_timeout: int
    llm_context_entries: int
    system_prompt: str
    auto_tag_count: int


class ConfigUpdate(BaseModel):
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_timeout: int | None = None
    llm_context_entries: int | None = None
    system_prompt: str | None = None
    auto_tag_count: int | None = None


class HealthOut(BaseModel):
    reachable: bool
    model: str | None = None
    error: str | None = None
