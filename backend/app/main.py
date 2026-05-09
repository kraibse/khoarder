from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _startup()
    yield


async def _startup():
    import pathlib

    from app.db.session import engine
    from app.db.base import Base
    import app.models  # noqa: F401 — registers all ORM models with Base

    # Ensure storage directories exist
    root = pathlib.Path(settings.storage_path)
    (root / "uploads").mkdir(parents=True, exist_ok=True)
    (root / "exports").mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Idempotent schema additions (until Alembic is set up)
    from sqlalchemy import text
    async with engine.begin() as conn:
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='entries' AND column_name='is_starred'"
        ))
        if result.scalar_one_or_none() is None:
            await conn.execute(text(
                "ALTER TABLE entries ADD COLUMN is_starred BOOLEAN NOT NULL DEFAULT FALSE"
            ))
        result2 = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='entries' AND column_name='img_url'"
        ))
        if result2.scalar_one_or_none() is None:
            await conn.execute(text(
                "ALTER TABLE entries ADD COLUMN img_url TEXT"
            ))
        # Make topic_id nullable for auto-categorization
        result3 = await conn.execute(text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name='entries' AND column_name='topic_id'"
        ))
        nullable = result3.scalar_one_or_none()
        if nullable == "NO":
            await conn.execute(text(
                "ALTER TABLE entries ALTER COLUMN topic_id DROP NOT NULL"
            ))
            await conn.execute(text(
                "ALTER TABLE entries DROP CONSTRAINT IF EXISTS entries_topic_id_fkey"
            ))
            await conn.execute(text(
                "ALTER TABLE entries ADD CONSTRAINT entries_topic_id_fkey "
                "FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE SET NULL"
            ))

    from app.db.session import AsyncSessionLocal
    from app.seed import seed_if_empty
    from app.services import config as config_svc

    async with AsyncSessionLocal() as db:
        # Load persisted config overrides from DB
        for key in ["llm_base_url", "llm_model", "llm_timeout", "llm_context_entries", "system_prompt"]:
            val = await config_svc.get_config_value(db, key, default="")
            if val:
                if key in ("llm_timeout", "llm_context_entries"):
                    setattr(settings, key, int(val))
                else:
                    setattr(settings, key, val)

        if settings.seed_demo_data:
            await seed_if_empty(db)


app = FastAPI(title="Knowledge Hoarder API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}
