from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.entry import Entry
from app.models.topic import Topic

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_search():
    import app.services.chat as chat_mod
    import app.services.search as search_mod

    async def _fake_search(db, query, topic_id=None, entry_type=None, limit=5):
        from sqlalchemy import select
        stmt = select(Entry).limit(limit)
        if topic_id:
            stmt = stmt.where(Entry.topic_id == topic_id)
        result = await db.execute(stmt)
        entries = list(result.scalars().all())
        return [(e, 0.0) for e in entries]

    original = search_mod.search
    search_mod.search = _fake_search
    yield
    search_mod.search = original


@pytest_asyncio.fixture
async def sample_topic(db_session: AsyncSession) -> Topic:
    topic = Topic(
        id=str(uuid.uuid4()),
        slug="test-topic",
        name="Test Topic",
        color="oklch(50% 0.1 200)",
        description="A topic for testing",
    )
    db_session.add(topic)
    await db_session.commit()
    await db_session.refresh(topic)
    return topic


@pytest_asyncio.fixture
async def sample_entry(db_session: AsyncSession, sample_topic: Topic) -> Entry:
    entry = Entry(
        id=str(uuid.uuid4()),
        topic_id=sample_topic.id,
        type="Article",
        title="Test Article",
        excerpt="This is a test article excerpt.",
        body="# Test Article\n\nThis is the body of the test article.",
        word_count=10,
        read_time_min=1,
        has_img=False,
        img_color="oklch(70% 0.05 200)",
        is_starred=False,
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)
    return entry
