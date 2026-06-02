from pydantic import BaseModel, Field
from datetime import datetime


class MemoryCreate(BaseModel):
    topic_id: str | None = None
    content: str = Field(..., min_length=1)
    type: str = "fact"
    trust_score: float = Field(default=1.0, ge=0.0, le=1.0)


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1)
    type: str | None = None
    trust_score: float | None = Field(default=None, ge=0.0, le=1.0)


class MemoryOut(BaseModel):
    id: str
    topic_id: str | None
    content: str
    type: str
    trust_score: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
