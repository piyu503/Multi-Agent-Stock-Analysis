from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyHealth(BaseModel):
    name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class AppHealth(BaseModel):
    status: str = "ok"
    name: str
    version: str
    environment: str
    uptime_seconds: float


class HealthResponse(BaseModel):
    status: HealthStatus = Field(
        ...,
        description="Overall service status: 'healthy' if all critical dependencies are up, 'degraded' if a dependency is down, 'unhealthy' if service itself is broken",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    app: AppHealth
    dependencies: Dict[str, DependencyHealth]
