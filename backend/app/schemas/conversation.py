from pydantic import BaseModel
from datetime import datetime


class ConversationCreate(BaseModel):
    topic_id: str | None = None
    title: str = "New Conversation"


class ConversationUpdate(BaseModel):
    title: str | None = None


class ConversationOut(BaseModel):
    id: str
    topic_id: str | None = None
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListOut(BaseModel):
    id: str
    topic_id: str | None = None
    title: str
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}
