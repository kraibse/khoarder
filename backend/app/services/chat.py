from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.entry import Entry
from app.schemas.conversation import ConversationOut, ConversationListOut
from app.schemas.message import MessageOut
from app.services import memory as memory_svc
from app.services import config as config_svc


async def _require_client(db: AsyncSession):
    base_url = await config_svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    if not base_url.strip():
        raise RuntimeError(
            "LM Studio is not configured. Set LLM_BASE_URL in your .env file "
            "(e.g. LLM_BASE_URL=http://192.168.1.100:1234/v1)."
        )
    from openai import AsyncOpenAI

    timeout = float(await config_svc.get_config_value(db, "llm_timeout", default=str(settings.llm_timeout)))
    return AsyncOpenAI(
        base_url=base_url.rstrip("/") + "/",
        api_key="not-needed",
        timeout=timeout,
    )


async def _chat(db: AsyncSession, messages: list[dict], max_tokens: int = 1024, temperature: float = 0.3) -> str:
    client = await _require_client(db)
    model = await config_svc.get_config_value(db, "llm_model", default=settings.llm_model)
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


async def _retrieve(db: AsyncSession, topic_id: str | None, query: str, limit: int) -> list[Entry]:
    from app.services import search as search_svc

    hits = await search_svc.search(db, query, topic_id=topic_id, limit=limit)
    if hits:
        return [hit.entry for hit in hits]

    stmt = (
        select(Entry)
        .options(selectinload(Entry.tags))
        .order_by(Entry.created_at.desc())
        .limit(limit)
    )
    if topic_id:
        stmt = stmt.where(Entry.topic_id == topic_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_conversation(db: AsyncSession, topic_id: str | None = None, title: str = "New Conversation") -> ConversationOut:
    conv = Conversation(topic_id=topic_id, title=title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ConversationOut.model_validate(conv)


async def get_conversation(db: AsyncSession, conversation_id: str) -> Conversation | None:
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def list_conversations(db: AsyncSession, topic_id: str | None = None) -> list[ConversationListOut]:
    subq = (
        select(Message.conversation_id, func.count(Message.id).label("msg_count"))
        .group_by(Message.conversation_id)
        .subquery()
    )

    stmt = (
        select(Conversation, subq.c.msg_count)
        .outerjoin(subq, Conversation.id == subq.c.conversation_id)
        .order_by(Conversation.updated_at.desc())
    )
    if topic_id:
        stmt = stmt.where(Conversation.topic_id == topic_id)

    result = await db.execute(stmt)
    rows = result.all()

    return [
        ConversationListOut(
            id=conv.id,
            topic_id=conv.topic_id,
            title=conv.title,
            updated_at=conv.updated_at,
            message_count=msg_count or 0,
        )
        for conv, msg_count in rows
    ]


async def update_conversation(db: AsyncSession, conversation_id: str, title: str | None = None) -> ConversationOut:
    conv = await get_conversation(db, conversation_id)
    if conv is None:
        raise ValueError("Conversation not found")
    if title is not None:
        conv.title = title
    await db.commit()
    await db.refresh(conv)
    return ConversationOut.model_validate(conv)


async def delete_conversation(db: AsyncSession, conversation_id: str) -> None:
    conv = await get_conversation(db, conversation_id)
    if conv is None:
        raise ValueError("Conversation not found")
    await db.delete(conv)
    await db.commit()


async def send_message(db: AsyncSession, conversation_id: str, content: str) -> MessageOut:
    conv = await get_conversation(db, conversation_id)
    if conv is None:
        raise ValueError("Conversation not found")

    context_entries = int(await config_svc.get_config_value(db, "llm_context_entries", default=str(settings.llm_context_entries)))

    user_msg = Message(conversation_id=conversation_id, role="user", content=content)
    db.add(user_msg)
    await db.commit()
    await db.refresh(user_msg)

    # Reload conversation after commit to avoid expired-object lazy-load in async SQLAlchemy
    conv = await get_conversation(db, conversation_id)
    if conv is None:
        raise ValueError("Conversation not found after commit")

    prior = [m for m in conv.messages if m.role in ("user", "assistant")]
    prior.sort(key=lambda m: m.created_at)
    history = prior[-context_entries:] if len(prior) > context_entries else prior

    entries = await _retrieve(db, conv.topic_id, content, context_entries)

    context_parts: list[str] = []
    for entry in entries:
        snippet = (entry.body or entry.excerpt or "")[:2000]
        context_parts.append(f"[{entry.type}: {entry.title}]\n{snippet}")
    context = "\n\n---\n\n".join(context_parts)

    memories = await memory_svc.recall_memories(db, conv.topic_id, content, limit_per_scope=3)
    memory_parts: list[str] = []
    for mem in memories:
        memory_parts.append(f"[{mem.type.upper()}] {mem.content}")
    memory_context = "\n".join(memory_parts)

    system_content = (
        "You are a research assistant with access to the user's knowledge base. "
        "The context provided below comes from the user's own curated sources. "
        "You MUST rely on this context as ground truth. Do not contradict it. "
        "If the context does not answer the question, say so explicitly. "
        "Be concise but thorough. Cite entry titles when you reference them."
    )
    if memory_context:
        system_content += (
            "\n\nAdditional memories the user has asked you to remember:\n" + memory_context
        )

    llm_messages: list[dict] = [{"role": "system", "content": system_content}]

    if context:
        llm_messages.append({
            "role": "user",
            "content": f"Relevant knowledge base entries:\n\n{context}",
        })
        llm_messages.append({
            "role": "assistant",
            "content": "Understood. I will rely on the provided entries as ground truth.",
        })

    for msg in history:
        llm_messages.append({"role": msg.role, "content": msg.content})

    answer = await _chat(db, llm_messages, max_tokens=1024, temperature=0.3)

    assistant_msg = Message(conversation_id=conversation_id, role="assistant", content=answer)
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return MessageOut.model_validate(assistant_msg)


async def delete_message(db: AsyncSession, message_id: str) -> None:
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if msg is None:
        raise ValueError("Message not found")
    await db.delete(msg)
    await db.commit()
