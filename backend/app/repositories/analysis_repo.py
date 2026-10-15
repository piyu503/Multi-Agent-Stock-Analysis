from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.analysis import AnalysisRun
from app.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository[AnalysisRun]):
    """Data access repository for AnalysisRun records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AnalysisRun, session)

    async def create(
        self,
        ticker: str,
        parameters: Optional[Dict[str, Any]] = None,
        status: str = "pending",
    ) -> AnalysisRun:
        run = AnalysisRun(
            ticker=ticker.upper().strip(),
            status=status,
            parameters=parameters or {},
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_by_id(self, run_id: uuid.UUID) -> Optional[AnalysisRun]:
        statement = select(AnalysisRun).where(AnalysisRun.id == run_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 20, offset: int = 0) -> List[AnalysisRun]:
        statement = (
            select(AnalysisRun)
            .order_by(AnalysisRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_status(
        self,
        run_id: uuid.UUID,
        status: str,
        result_summary: Optional[str] = None,
    ) -> Optional[AnalysisRun]:
        run = await self.get_by_id(run_id)
        if run:
            run.status = status
            if result_summary is not None:
                run.result_summary = result_summary
            await self.session.flush()
            await self.session.refresh(run)
        return run
