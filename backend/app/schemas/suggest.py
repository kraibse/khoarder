from pydantic import BaseModel, Field


class SuggestRequest(BaseModel):
    query: str = ""               # optional refine query from the sidebar input
    offset: int = 0
    limit: int = Field(5, ge=1, le=20)


class SuggestionOut(BaseModel):
    id: str
    title: str
    excerpt: str
    source: str
    source_url: str
    type: str = "Article"
    relevance: float = 0.5
    tags: list[str] = []
    provider: str = ""
