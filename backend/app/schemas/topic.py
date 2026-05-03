from pydantic import BaseModel


class TopicOut(BaseModel):
    id: str
    slug: str
    name: str
    color: str
    description: str
    count: int = 0

    model_config = {"from_attributes": True}


class TopicCreate(BaseModel):
    name: str
    description: str = ""
    color: str = "oklch(55% 0.12 200)"


class TopicUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
