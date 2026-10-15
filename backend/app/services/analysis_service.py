from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import EntityNotFoundError
from app.core.logging import get_logger
from app.models.analysis import AnalysisRun
from app.repositories.analysis_repo import AnalysisRepository
from app.schemas.analysis import AnalysisRunCreate

logger = get_logger(__name__)


class AnalysisService:
    """Service handling orchestration of stock analysis runs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AnalysisRepository(session)

    async def initiate_analysis(self, payload: AnalysisRunCreate) -> AnalysisRun:
        """Create a new analysis record ready for multi-agent dispatch."""
        logger.info(f"Initiating analysis for ticker: {payload.ticker}")
        run = await self.repo.create(
            ticker=payload.ticker,
            parameters={
                "agent_types": payload.agent_types,
                "custom_params": payload.parameters,
            },
            status="pending",
        )
        return run

    async def get_analysis(self, run_id: uuid.UUID) -> AnalysisRun:
        """Fetch an analysis run by ID."""
        run = await self.repo.get_by_id(run_id)
        if not run:
            raise EntityNotFoundError("AnalysisRun", run_id)
        return run

    async def list_recent_analyses(self, limit: int = 10, offset: int = 0) -> List[AnalysisRun]:
        """List historical analysis runs."""
        return await self.repo.list_recent(limit=limit, offset=offset)
