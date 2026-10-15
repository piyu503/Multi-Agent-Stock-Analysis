from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db_session
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health and Readiness Check",
    description="Returns service health status, application metadata, and dependency connectivity status.",
)
async def check_health(
    session: AsyncSession = Depends(get_db_session),
) -> HealthResponse:
    """Check application readiness and verify database connectivity."""
    service = HealthService(session=session)
    return await service.get_health()
