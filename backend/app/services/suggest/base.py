from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Suggestion:
    """A single suggested entry from an external source."""
    id: str                  # stable id "{provider}:{external_id}" — frontend dedupe key
    title: str
    excerpt: str
    source: str              # display label, e.g. "Wikipedia · Tonegawa, 2015"
    source_url: str          # canonical URL — fed back into POST /entries/import-url
    type: str = "Article"    # Article | Paper | Reference | Note
    relevance: float = 0.5   # 0..1
    tags: list[str] = None  # type: ignore[assignment]
    provider: str = ""       # provider name (wikipedia, arxiv, …)

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class Provider(ABC):
    """A discovery provider — talks to one external source."""

    name: str = ""           # short identifier
    weight: float = 1.0      # relative trust for ranking

    @abstractmethod
    async def fetch(self, query: str, limit: int = 10) -> list[Suggestion]:
        """Run a query against the provider and return raw suggestions.

        Implementations MUST swallow network errors and return [] — the
        orchestrator runs providers in parallel and a single failure must
        not abort the batch.
        """
        ...


# Topic context passed through ranker / LLM
@dataclass
class TopicContext:
    name: str
    description: str = ""
    sample_titles: list[str] = None       # type: ignore[assignment]
    sample_tags: list[str] = None         # type: ignore[assignment]
    refine_query: str = ""

    def __post_init__(self):
        if self.sample_titles is None:
            self.sample_titles = []
        if self.sample_tags is None:
            self.sample_tags = []

    def keywords(self) -> list[str]:
        """Tokenized keyword set used for overlap ranking."""
        terms: list[str] = []
        for src in (self.name, self.description, self.refine_query):
            for tok in src.lower().split():
                tok = tok.strip(",.!?;:\"'()[]")
                if len(tok) > 2:
                    terms.append(tok)
        for tag in self.sample_tags:
            terms.append(tag.lower())
        # Dedupe preserving order
        seen: set[str] = set()
        out: list[str] = []
        for t in terms:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out
