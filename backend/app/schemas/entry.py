from datetime import datetime

from pydantic import BaseModel, HttpUrl, field_validator


class EntryOut(BaseModel):
    id: str
    topic_id: str | None
    type: str
    title: str
    excerpt: str
    tags: list[str] = []
    date: str  # ISO date string for frontend compatibility
    source: str | None = None
    has_img: bool
    img_url: str | None = None
    img_height: int | None = None
    img_color: str
    is_starred: bool = False
    backlink_count: int = 0
    headline: str | None = None  # populated only in search results

    model_config = {"from_attributes": True}


class ArticleDetailOut(EntryOut):
    body: str
    word_count: int
    read_time_min: int
    source_url: str | None = None


class BacklinkOut(BaseModel):
    id: str
    relation_id: str
    title: str
    type: str
    refs: int

    model_config = {"from_attributes": True}


class RelatedEntryOut(BaseModel):
    id: str
    relation_id: str
    title: str
    type: str
    img_color: str

    model_config = {"from_attributes": True}


VALID_TYPES = {"Article", "Note", "Paper", "Excerpt", "Reference"}

IMG_COLORS = [
    "oklch(72% 0.08 200)", "oklch(65% 0.10 160)", "oklch(68% 0.07 30)",
    "oklch(60% 0.09 280)", "oklch(74% 0.06 80)", "oklch(62% 0.11 320)",
    "oklch(70% 0.08 120)", "oklch(67% 0.09 240)", "oklch(75% 0.05 50)",
    "oklch(63% 0.10 190)", "oklch(71% 0.07 340)", "oklch(66% 0.08 100)",
]


class TopicSuggestionCreate(BaseModel):
    name: str
    description: str = ""
    color: str


class EntryCreate(BaseModel):
    topic_id: str | None = None
    type: str = "Note"
    title: str
    excerpt: str = ""
    body: str = ""
    source_url: str | None = None
    source_label: str | None = None
    has_img: bool = False
    img_url: str | None = None
    is_starred: bool = False
    tags: list[str] = []
    topic_suggestion: TopicSuggestionCreate | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_TYPES:
            raise ValueError(f"type must be one of {sorted(VALID_TYPES)}")
        return v


class URLImportRequest(BaseModel):
    topic_id: str | None = None
    url: str
    topic_suggestion: TopicSuggestionCreate | None = None


class TopicSuggestionOut(BaseModel):
    name: str
    description: str = ""
    color: str
    is_new: bool = False


class TopicPreviewRequest(BaseModel):
    title: str
    excerpt: str = ""
    body: str = ""
    feedback: str | None = None


class URLPreviewOut(BaseModel):
    title: str
    excerpt: str
    body: str
    has_img: bool
    img_url: str | None = None
    suggestion: TopicSuggestionOut | None = None
    partial: bool = False  # True when body content could not be fully extracted


class EntryUpdate(BaseModel):
    title: str | None = None
    type: str | None = None
    body: str | None = None
    excerpt: str | None = None
    source_url: str | None = None
    source_label: str | None = None
    is_starred: bool | None = None
    img_url: str | None = None
    tags: list[str] | None = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_TYPES:
            raise ValueError(f"type must be one of {sorted(VALID_TYPES)}")
        return v
