import time
from typing import Optional, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger

logger = get_logger(__name__)


class HealthRepository:
    """Repository responsible for evaluating low-level dependency health."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.session = session

    async def ping_database(self) -> Tuple[bool, Optional[float], Optional[str]]:
        """Perform a SELECT 1 query to test active database connectivity and measure latency.
        
        Returns:
            Tuple of (is_healthy, latency_ms, error_message)
        """
        if self.session is None:
            return False, None, "No active database session available"

        start_time = time.perf_counter()
        try:
            result = await self.session.execute(text("SELECT 1"))
            val = result.scalar()
            latency = (time.perf_counter() - start_time) * 1000.0
            if val == 1:
                return True, round(latency, 2), None
            return False, round(latency, 2), "Unexpected response from database ping query"
        except Exception as exc:
            latency = (time.perf_counter() - start_time) * 1000.0
            error_msg = f"Database ping failed: {type(exc).__name__}"
            logger.warning(f"{error_msg} (detail: {str(exc)})")
            return False, round(latency, 2), error_msg
