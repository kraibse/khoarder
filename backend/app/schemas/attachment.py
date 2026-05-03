from datetime import datetime

from pydantic import BaseModel


class AttachmentOut(BaseModel):
    id: str
    filename: str
    ext: str
    size_bytes: int
    created_at: datetime

    model_config = {"from_attributes": True}
