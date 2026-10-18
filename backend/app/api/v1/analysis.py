from typing import Any, Dict, List
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.llm.exceptions import (
    LLMConnectionError,
    LLMError,
    LLMModelNotFoundError,
    LLMParsingError,
    LLMTimeoutError,
)
from app.core.llm.factory import get_llm_provider
from app.database.session import get_db_session
from app.schemas.analysis import AnalysisRunCreate, AnalysisRunResponse
from app.schemas.technical_analysis import TechnicalAnalysisRequest, TechnicalAnalysisResponse
from app.services.analysis_service import AnalysisService
from app.services.technical_analyst import TechnicalAnalystService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post(
    "/technical",
    response_model=TechnicalAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Technical Stock Analysis",
    description=(
        "Fetch validated market data and deterministic indicators, then execute a structured "
        "evidence-driven technical analysis using the configured LLM provider (Ollama / DeepSeek-R1 by default)."
    ),
)
async def run_technical_analysis(
    payload: TechnicalAnalysisRequest,
) -> TechnicalAnalysisResponse:
    """Execute technical analysis on the target equity symbol."""
    service = TechnicalAnalystService()
    try:
        return await service.analyze(ticker=payload.ticker, period=payload.period)
    except LLMConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local LLM provider unavailable: {e.message}",
        ) from e
    except LLMModelNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Configured model not found on LLM provider: {e.message}",
        ) from e
    except LLMTimeoutError as e:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"LLM inference timed out: {e.message}",
        ) from e
    except LLMParsingError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM produced unparseable or schema-violating output: {e.message}",
        ) from e
    except LLMError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LLM inference error: {e.message}",
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/provider-status",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get LLM Provider Health & Diagnostics",
    description="Check the availability of the configured LLM provider and verify local model installation.",
)
async def get_provider_status() -> Dict[str, Any]:
    """Retrieve diagnostic health status of the active LLM provider."""
    provider = get_llm_provider()
    return await provider.check_health()


@router.post(
    "",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate Stock Analysis",
    description="Enqueue a stock analysis pipeline for a target ticker symbol across agent roles.",
)
async def create_analysis(
    payload: AnalysisRunCreate,
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisRunResponse:
    service = AnalysisService(session)
    return await service.initiate_analysis(payload)


@router.get(
    "/{run_id}",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Analysis Run Status",
    description="Retrieve status and results for a specific stock analysis execution run.",
)
async def get_analysis(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AnalysisRunResponse:
    service = AnalysisService(session)
    return await service.get_analysis(run_id)


@router.get(
    "",
    response_model=List[AnalysisRunResponse],
    status_code=status.HTTP_200_OK,
    summary="List Recent Analysis Runs",
    description="Retrieve historical analysis execution runs.",
)
async def list_analyses(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> List[AnalysisRunResponse]:
    service = AnalysisService(session)
    return await service.list_recent_analyses(limit=limit, offset=offset)

