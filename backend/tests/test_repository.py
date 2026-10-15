import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.analysis_repo import AnalysisRepository
from app.schemas.analysis import AnalysisRunCreate
from app.services.analysis_service import AnalysisService


@pytest.mark.asyncio
async def test_analysis_repository_crud(db_session: AsyncSession):
    """Test repository create, read, and update operations."""
    repo = AnalysisRepository(db_session)

    # 1. Create run
    run = await repo.create(
        ticker="NVDA",
        parameters={"model": "gemini-pro", "timeframe": "1y"},
        status="pending",
    )
    assert run.id is not None
    assert run.ticker == "NVDA"
    assert run.status == "pending"
    assert run.parameters["model"] == "gemini-pro"

    # 2. Get by ID
    fetched = await repo.get_by_id(run.id)
    assert fetched is not None
    assert fetched.id == run.id
    assert fetched.ticker == "NVDA"

    # 3. Update status
    updated = await repo.update_status(
        run.id,
        status="completed",
        result_summary="Target valuation upside calculated at +18%.",
    )
    assert updated is not None
    assert updated.status == "completed"
    assert "upside" in (updated.result_summary or "")


@pytest.mark.asyncio
async def test_analysis_service_flow(db_session: AsyncSession):
    """Test service orchestration layer."""
    service = AnalysisService(db_session)
    payload = AnalysisRunCreate(
        ticker="MSFT",
        agent_types=["fundamentals", "bull", "bear"],
        parameters={"discount_rate": 0.08},
    )

    run = await service.initiate_analysis(payload)
    assert run.id is not None
    assert run.ticker == "MSFT"

    fetched = await service.get_analysis(run.id)
    assert fetched.id == run.id

    history = await service.list_recent_analyses(limit=5)
    assert len(history) >= 1
    assert any(r.ticker == "MSFT" for r in history)
