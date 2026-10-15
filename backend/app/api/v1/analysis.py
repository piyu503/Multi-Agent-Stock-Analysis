from typing import List
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db_session
from app.schemas.analysis import AnalysisRunCreate, AnalysisRunResponse
from app.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["Analysis"])


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
