from pydantic import BaseModel


# ── Q&A ───────────────────────────────────────────────────────────────────────

class QARequest(BaseModel):
    question: str
    topic_id: str


class QASource(BaseModel):
    id: str
    title: str
    type: str
    snippet: str


class QAResponse(BaseModel):
    answer: str
    sources: list[QASource]


# ── Article assistance ────────────────────────────────────────────────────────

class AssistSummarizeRequest(BaseModel):
    entry_id: str


class AssistSummarizeResponse(BaseModel):
    summary: str


class AssistTagsRequest(BaseModel):
    entry_id: str


class AssistTagsResponse(BaseModel):
    tags: list[str]


class AssistRelatedRequest(BaseModel):
    entry_id: str


class AssistRelatedEntry(BaseModel):
    id: str
    title: str
    type: str
    img_color: str


class AssistRelatedResponse(BaseModel):
    entries: list[AssistRelatedEntry]


class AssistExtendRequest(BaseModel):
    entry_id: str
    prompt: str = ""  # optional user direction


class AssistExtendResponse(BaseModel):
    extension: str


# ── Status ────────────────────────────────────────────────────────────────────

class QAStatusResponse(BaseModel):
    configured: bool
    model: str | None
