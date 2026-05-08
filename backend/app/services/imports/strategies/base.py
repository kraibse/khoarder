"""FetchStrategy abstract base.

Each strategy is responsible for *acquisition only*: take a URL, return raw HTML
plus diagnostics. Extraction is a separate stage so any strategy's HTML can be
fed through the same Trafilatura/Readability/lxml pipeline.
"""
from __future__ import annotations

import abc

from app.services.imports.types import AcquireResult, ImportRequest


class FetchStrategy(abc.ABC):
    """Implementations should be cheap to instantiate; orchestrator builds them per import."""

    name: str = "base"

    @abc.abstractmethod
    def is_available(self, req: ImportRequest) -> bool:
        """True when this strategy is configured + reachable to attempt."""
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch(self, req: ImportRequest) -> AcquireResult:
        """Acquire raw HTML. Must return a structured AcquireResult, never raise."""
        raise NotImplementedError
