from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


class TestConversations:
    async def test_create_conversation(self, client: AsyncClient):
        payload = {"topic_id": None, "title": "Test Chat"}
        resp = await client.post("/api/conversations", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Chat"
        assert data["topic_id"] is None

    async def test_list_conversations(self, client: AsyncClient, db_session: AsyncSession):
        conv = Conversation(
            id=str(uuid.uuid4()),
            title="Existing Chat",
            topic_id=None,
        )
        db_session.add(conv)
        await db_session.commit()

        resp = await client.get("/api/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Existing Chat"

    async def test_get_conversation(self, client: AsyncClient, db_session: AsyncSession):
        conv = Conversation(
            id=str(uuid.uuid4()),
            title="My Chat",
            topic_id=None,
        )
        db_session.add(conv)
        await db_session.commit()

        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            role="user",
            content="Hello",
        )
        db_session.add(msg)
        await db_session.commit()

        resp = await client.get(f"/api/conversations/{conv.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "My Chat"
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Hello"

    async def test_delete_conversation(self, client: AsyncClient, db_session: AsyncSession):
        conv = Conversation(
            id=str(uuid.uuid4()),
            title="To Delete",
            topic_id=None,
        )
        db_session.add(conv)
        await db_session.commit()

        resp = await client.delete(f"/api/conversations/{conv.id}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/conversations/{conv.id}")
        assert resp.status_code == 404

    async def test_rename_conversation(self, client: AsyncClient, db_session: AsyncSession):
        conv = Conversation(
            id=str(uuid.uuid4()),
            title="Old Title",
            topic_id=None,
        )
        db_session.add(conv)
        await db_session.commit()

        resp = await client.patch(f"/api/conversations/{conv.id}", json={"title": "New Title"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New Title"


class TestMessages:
    async def test_send_message(self, client: AsyncClient, db_session: AsyncSession):
        conv = Conversation(
            id=str(uuid.uuid4()),
            title="Chat",
            topic_id=None,
        )
        db_session.add(conv)
        await db_session.commit()

        resp = await client.post(f"/api/conversations/{conv.id}/messages", json={"content": "Hi"})
        assert resp.status_code == 503

    async def test_delete_message(self, client: AsyncClient, db_session: AsyncSession):
        conv = Conversation(
            id=str(uuid.uuid4()),
            title="Chat",
            topic_id=None,
        )
        db_session.add(conv)
        await db_session.commit()

        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            role="user",
            content="Delete me",
        )
        db_session.add(msg)
        await db_session.commit()

        resp = await client.delete(f"/api/conversations/{conv.id}/messages/{msg.id}")
        assert resp.status_code == 204
