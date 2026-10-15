import time
from datetime import datetime, timezone
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_settings
from app.core.logging import get_logger
from app.repositories.health_repo import HealthRepository
from app.schemas.health import (
    AppHealth,
    DependencyHealth,
    HealthResponse,
    HealthStatus,
)

logger = get_logger(__name__)
_START_TIME = time.time()


class HealthService:
    """Service orchestrating application and dependency health status."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.health_repo = HealthRepository(session=session)
        self.settings = get_settings()

    async def get_health(self) -> HealthResponse:
        """Evaluate application uptime and check dependencies like the database.
        
        Distinguishes application state from dependency state:
        If database ping fails, application is still running but status is 'degraded'.
        """
        uptime = round(time.time() - _START_TIME, 2)
        dependencies: Dict[str, DependencyHealth] = {}

        # 1. Database Connectivity Check
        is_db_healthy, db_latency, db_err = await self.health_repo.ping_database()
        dependencies["database"] = DependencyHealth(
            name="postgresql",
            status=HealthStatus.HEALTHY if is_db_healthy else HealthStatus.UNHEALTHY,
            latency_ms=db_latency,
            message="Database reachable and responsive" if is_db_healthy else (db_err or "Connection failed"),
        )

        # 2. Determine Overall Health Status
        # App is healthy if critical dependencies respond; degraded if non-fatal or DB is temporarily down.
        if is_db_healthy:
            overall_status = HealthStatus.HEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        app_info = AppHealth(
            status="ok",
            name=self.settings.PROJECT_NAME,
            version=self.settings.VERSION,
            environment=self.settings.ENVIRONMENT,
            uptime_seconds=uptime,
        )

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            app=app_info,
            dependencies=dependencies,
        )
