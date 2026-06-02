from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entry import Entry
from app.models.topic import Topic


class TestListEntries:
    async def test_empty_topic(self, client: AsyncClient, sample_topic: Topic):
        resp = await client.get(f"/api/entries?topic_id={sample_topic.id}")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_by_topic(self, client: AsyncClient, sample_entry: Entry):
        resp = await client.get(f"/api/entries?topic_id={sample_entry.topic_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Article"
        assert data[0]["type"] == "Article"

    async def test_filter_by_type(self, client: AsyncClient, sample_entry: Entry):
        resp = await client.get(f"/api/entries?topic_id={sample_entry.topic_id}&type=Note")
        assert resp.status_code == 200
        assert resp.json() == []

        resp = await client.get(f"/api/entries?topic_id={sample_entry.topic_id}&type=Article")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_sort_order(self, client: AsyncClient, db_session: AsyncSession, sample_topic: Topic):
        for i in range(3):
            entry = Entry(
                id=str(uuid.uuid4()),
                topic_id=sample_topic.id,
                type="Article",
                title=f"Article {i}",
                excerpt="excerpt",
                body="body",
                word_count=1,
                read_time_min=1,
                has_img=False,
                img_color="oklch(70% 0.05 200)",
            )
            db_session.add(entry)
        await db_session.commit()

        resp = await client.get(f"/api/entries?topic_id={sample_topic.id}&sort=date_desc")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        assert data[0]["title"] == "Article 2"

        resp = await client.get(f"/api/entries?topic_id={sample_topic.id}&sort=date_asc")
        data = resp.json()
        assert data[0]["title"] == "Article 0"

    async def test_get_single_entry(self, client: AsyncClient, sample_entry: Entry):
        resp = await client.get(f"/api/entries/{sample_entry.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Article"
        assert data["body"] == "# Test Article\n\nThis is the body of the test article."
        assert data["word_count"] == 10

    async def test_get_nonexistent_entry(self, client: AsyncClient):
        resp = await client.get("/api/entries/nonexistent-id")
        assert resp.status_code == 404


class TestCreateUpdateDelete:
    async def test_create_entry(self, client: AsyncClient, sample_topic: Topic):
        payload = {
            "topic_id": sample_topic.id,
            "type": "Note",
            "title": "New Note",
            "excerpt": "A new note",
            "body": "Body text",
        }
        resp = await client.post("/api/entries", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Note"
        assert data["type"] == "Note"

    async def test_update_entry(self, client: AsyncClient, sample_entry: Entry):
        payload = {"title": "Updated Title", "is_starred": True}
        resp = await client.patch(f"/api/entries/{sample_entry.id}", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated Title"
        assert data["is_starred"] is True

    async def test_delete_entry(self, client: AsyncClient, sample_entry: Entry):
        resp = await client.delete(f"/api/entries/{sample_entry.id}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/entries/{sample_entry.id}")
        assert resp.status_code == 404


class TestBacklinks:
    async def test_no_backlinks(self, client: AsyncClient, sample_entry: Entry):
        resp = await client.get(f"/api/entries/{sample_entry.id}/backlinks")
        assert resp.status_code == 200
        assert resp.json() == []
