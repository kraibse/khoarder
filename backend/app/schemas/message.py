from pydantic import BaseModel
from datetime import datetime


class MessageCreate(BaseModel):
    content: str


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: datetime
    entry_id: str | None = None

    model_config = {"from_attributes": True}


class ConversationWithMessagesOut(BaseModel):
    id: str
    topic_id: str | None = None
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []

    model_config = {"from_attributes": True}
