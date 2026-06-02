import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.conversation import ConversationCreate, ConversationOut, ConversationListOut, ConversationUpdate, ConversationWithMessagesOut
from app.schemas.message import MessageOut, MessageCreate
from app.services import chat as chat_svc

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(body: ConversationCreate, db: AsyncSession = Depends(get_db)):
    return await chat_svc.create_conversation(db, topic_id=body.topic_id, title=body.title)


@router.get("", response_model=list[ConversationListOut])
async def list_conversations(
    topic_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await chat_svc.list_conversations(db, topic_id=topic_id)


@router.get("/{conversation_id}", response_model=ConversationWithMessagesOut)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    conv = await chat_svc.get_conversation(db, conversation_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = [MessageOut.model_validate(m) for m in conv.messages]
    return ConversationWithMessagesOut(
        id=conv.id,
        topic_id=conv.topic_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=messages,
    )


@router.patch("/{conversation_id}", response_model=ConversationOut)
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await chat_svc.update_conversation(db, conversation_id, title=body.title)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await chat_svc.delete_conversation(db, conversation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.post("/{conversation_id}/messages", response_model=MessageOut, status_code=201)
async def send_message(
    conversation_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await chat_svc.send_message(db, conversation_id, content=body.content)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str,
    body: MessageCreate,
    db: AsyncSession = Depends(get_db),
):
    """Stream assistant response as Server-Sent Events."""
    try:
        async def event_generator():
            async for token in chat_svc.stream_send_message(db, conversation_id, content=body.content):
                payload = json.dumps({"type": "token", "content": token})
                yield f"data: {payload}\n\n"

            # Fetch the persisted assistant message
            conv = await chat_svc.get_conversation(db, conversation_id)
            if conv and conv.messages:
                last = max(conv.messages, key=lambda m: m.created_at)
                if last.role == "assistant":
                    done = json.dumps(
                        {
                            "type": "done",
                            "message": MessageOut.model_validate(last).model_dump(mode="json"),
                        }
                    )
                    yield f"data: {done}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.delete("/{conversation_id}/messages/{message_id}", status_code=204)
async def delete_message(
    conversation_id: str,
    message_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        await chat_svc.delete_message(db, message_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Message not found")
