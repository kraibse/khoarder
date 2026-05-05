"""Find-more suggestions — pluggable provider architecture.

Mirrors the pattern in app.services.search:
- `Provider` ABC + `Suggestion` dataclass live in `base.py`.
- Concrete providers in `providers.py` (Wikipedia, arXiv, Semantic Scholar,
  OpenAlex, Hacker News Algolia) and `searxng.py` (optional metasearch).
- Optional LLM steps in `llm.py` (query expansion + relevance reranker).
- `orchestrator.suggest()` runs all enabled providers in parallel,
  dedupes by URL, scores by source-weight × keyword-overlap × recency,
  optionally reranks with LM Studio when configured.
"""
from app.services.suggest.base import Provider, Suggestion
from app.services.suggest.orchestrator import suggest

__all__ = ["Provider", "Suggestion", "suggest"]
