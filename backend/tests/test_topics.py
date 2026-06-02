from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.topic import Topic
from app.schemas.topic import TopicCreate, TopicUpdate
from app.services import topics as svc


class TestListTopics:
    async def test_empty_list(self, db_session: AsyncSession):
        result = await svc.list_topics(db_session)
        assert result == []

    async def test_returns_topics_with_counts(self, db_session: AsyncSession):
        topic = Topic(
            id=str(uuid.uuid4()),
            slug="science",
            name="Science",
            color="oklch(50% 0.1 200)",
            description="Science topics",
        )
        db_session.add(topic)
        await db_session.commit()

        entry = Entry(
            id=str(uuid.uuid4()),
            topic_id=topic.id,
            type="Article",
            title="Gravity",
            excerpt="About gravity",
            body="Gravity is a force.",
            word_count=4,
            read_time_min=1,
            has_img=False,
            img_color="oklch(70% 0.05 200)",
        )
        db_session.add(entry)
        await db_session.commit()

        result = await svc.list_topics(db_session)
        assert len(result) == 1
        assert result[0].name == "Science"
        assert result[0].count == 1


class TestGetTopic:
    async def test_existing_topic(self, db_session: AsyncSession):
        topic = Topic(
            id=str(uuid.uuid4()),
            slug="tech",
            name="Technology",
            color="oklch(60% 0.1 180)",
            description="Tech stuff",
        )
        db_session.add(topic)
        await db_session.commit()

        result = await svc.get_topic(db_session, topic.id)
        assert result is not None
        assert result.name == "Technology"

    async def test_missing_topic(self, db_session: AsyncSession):
        result = await svc.get_topic(db_session, "nonexistent-id")
        assert result is None


class TestCreateTopic:
    async def test_create_basic(self, db_session: AsyncSession):
        data = TopicCreate(name="History", description="Historical events")
        result = await svc.create_topic(db_session, data)
        assert result.name == "History"
        assert result.slug == "history"
        assert result.count == 0

    async def test_duplicate_name_gets_unique_slug(self, db_session: AsyncSession):
        data = TopicCreate(name="Duplicate", description="First")
        await svc.create_topic(db_session, data)

        data2 = TopicCreate(name="Duplicate", description="Second")
        result = await svc.create_topic(db_session, data2)
        assert result.slug == "duplicate-2"


class TestUpdateTopic:
    async def test_update_name(self, db_session: AsyncSession):
        topic = Topic(
            id=str(uuid.uuid4()),
            slug="old-name",
            name="Old Name",
            color="oklch(50% 0.1 200)",
            description="",
        )
        db_session.add(topic)
        await db_session.commit()

        result = await svc.update_topic(db_session, topic.id, TopicUpdate(name="New Name"))
        assert result is not None
        assert result.name == "New Name"
        assert result.slug == "new-name"

    async def test_update_nonexistent(self, db_session: AsyncSession):
        result = await svc.update_topic(db_session, "missing-id", TopicUpdate(name="X"))
        assert result is None


class TestGetTopicTags:
    async def test_no_entries_returns_empty(self, db_session: AsyncSession):
        topic = Topic(
            id=str(uuid.uuid4()),
            slug="empty",
            name="Empty",
            color="oklch(50% 0.1 200)",
            description="",
        )
        db_session.add(topic)
        await db_session.commit()

        result = await svc.get_topic_tags(db_session, topic.id)
        assert result == []
