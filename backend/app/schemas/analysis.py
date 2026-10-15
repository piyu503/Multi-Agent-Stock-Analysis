from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisRunCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol (e.g. AAPL, MSFT)")
    agent_types: List[str] = Field(
        default=["fundamentals", "technical", "risk"],
        description="List of AI agent roles to include in the analysis pipeline",
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Custom execution parameters and filters for the agent workflow",
    )


class AnalysisRunResponse(BaseModel):
    id: uuid.UUID
    ticker: str
    status: AnalysisStatus
    parameters: Dict[str, Any]
    result_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
