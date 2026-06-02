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
from app.services import config as config_svc

router = APIRouter(tags=["qa"])


@router.get("/qa/status", response_model=QAStatusResponse)
async def qa_status(db: AsyncSession = Depends(get_db)):
    """Check whether LM Studio is configured (does not ping the endpoint)."""
    base_url = await config_svc.get_config_value(db, "llm_base_url", default=settings.llm_base_url)
    configured = bool(base_url.strip())
    model = await config_svc.get_config_value(db, "llm_model", default=settings.llm_model) if configured else None
    return QAStatusResponse(
        configured=configured,
        model=model,
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
