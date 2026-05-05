from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:dev@localhost/khoarder"
    storage_path: str = "./storage"
    max_upload_bytes: int = 100 * 1024 * 1024  # 100 MB
    search_backend: str = "postgres"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:80"]

    # LM Studio — OpenAI-compatible API running on a separate device
    llm_base_url: str = ""          # e.g. http://192.168.1.100:1234/v1
    llm_model: str = "local-model"  # model name shown in LM Studio
    llm_timeout: int = 60           # seconds per request
    llm_context_entries: int = 5    # retrieved entries sent as context per Q&A
    system_prompt: str = ""         # custom system prompt for extension drafting
    auto_tag_count: int = 3         # number of tags to auto-generate for new entries

    # Camoufox — stealth headless browser sidecar for JS-heavy / bot-protected sites
    camoufox_enabled: bool = False                          # use camoufox when standard extractors return empty content
    camoufox_timeout: int = 30                              # seconds to wait for page load
    camoufox_url: str = "http://camoufox-browser:3392"     # URL of the camoufox-browser container

    # Find-more discovery — pluggable providers + optional LLM steps
    suggest_searxng_url: str = ""                # optional self-hosted SearXNG base URL
    suggest_use_llm_expand: bool = False         # let LM Studio invent extra search queries
    suggest_use_llm_rerank: bool = False         # let LM Studio rerank candidates by topic relevance


settings = Settings()
