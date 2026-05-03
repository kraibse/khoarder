from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.schemas.qa import (
    AssistExtendRequest,
    AssistExtendResponse,
    AssistRelatedRequest,
    AssistRelatedResponse,
    AssistSummarizeRequest,
    AssistSummarizeResponse,
    AssistTagsRequest,
    AssistTagsResponse,
    QARequest,
    QAResponse,
    QAStatusResponse,
)
from app.services import qa as svc

router = APIRouter(tags=["qa"])


@router.get("/qa/status", response_model=QAStatusResponse)
async def qa_status():
    """Check whether LM Studio is configured (does not ping the endpoint)."""
    configured = bool(settings.llm_base_url.strip())
    return QAStatusResponse(
        configured=configured,
        model=settings.llm_model if configured else None,
    )


def _lm_error(exc: Exception) -> HTTPException:
    msg = str(exc)
    if "connection" in msg.lower() or "connect" in msg.lower() or "unreachable" in msg.lower():
        return HTTPException(status_code=503, detail="LM Studio is unreachable. Check the base URL and ensure LM Studio is running.")
    if "timeout" in msg.lower():
        return HTTPException(status_code=504, detail="LM Studio request timed out. Try increasing the timeout in Settings.")
    return HTTPException(status_code=502, detail=f"LM Studio error: {msg}")


@router.post("/qa", response_model=QAResponse)
async def ask(body: QARequest, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.ask_question(db, body.question, body.topic_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise _lm_error(exc)


@router.post("/assist/summarize", response_model=AssistSummarizeResponse)
async def summarize(body: AssistSummarizeRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.assist_summarize(db, body.entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise _lm_error(exc)


@router.post("/assist/tags", response_model=AssistTagsResponse)
async def suggest_tags(body: AssistTagsRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.assist_tags(db, body.entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise _lm_error(exc)


@router.post("/assist/related", response_model=AssistRelatedResponse)
async def suggest_related(body: AssistRelatedRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.assist_related(db, body.entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise _lm_error(exc)


@router.post("/assist/extend", response_model=AssistExtendResponse)
async def draft_extension(body: AssistExtendRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.assist_extend(db, body.entry_id, body.prompt)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise _lm_error(exc)
