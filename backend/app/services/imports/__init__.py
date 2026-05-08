"""Tiered URL import pipeline.

Public entrypoint:
    from app.services.imports import import_url, ImportOrchestrator

The orchestrator picks the cheapest fetch strategy that is likely to succeed,
escalates only when the previous tier returned a low-quality / blocked / empty
result, and records per-origin success history so future imports can short-circuit.
"""
from app.services.imports.orchestrator import ImportOrchestrator, import_url
from app.services.imports.types import (
    AcquireResult,
    ChallengeType,
    Diagnostics,
    ExtractionResult,
    ImportRequest,
    ImportResult,
    QualityScore,
    StageTiming,
)

__all__ = [
    "AcquireResult",
    "ChallengeType",
    "Diagnostics",
    "ExtractionResult",
    "ImportOrchestrator",
    "ImportRequest",
    "ImportResult",
    "QualityScore",
    "StageTiming",
    "import_url",
]
