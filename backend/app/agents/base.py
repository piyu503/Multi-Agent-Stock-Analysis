from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentMetadata(BaseModel):
    """Metadata describing an agent's identity, role, and capabilities."""
    name: str
    role: str
    description: str
    version: str = "1.0.0"
    model_provider: str = "gemini"


class AgentInput(BaseModel):
    """Normalized input payload provided to an agent."""
    ticker: str
    context: Dict[str, Any] = Field(default_factory=dict)
    prior_findings: Optional[List[Dict[str, Any]]] = None


class AgentOutput(BaseModel):
    """Normalized output produced by an agent."""
    agent_name: str
    summary: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    data: Dict[str, Any] = Field(default_factory=dict)
    citations: List[str] = Field(default_factory=list)
    errors: Optional[List[str]] = None


class BaseStockAgent(ABC):
    """Abstract Base Class for all specialized financial analysis agents."""

    def __init__(self, metadata: AgentMetadata) -> None:
        self.metadata = metadata

    @abstractmethod
    async def run(self, input_data: AgentInput) -> AgentOutput:
        """Execute agent reasoning and tool usage for the specified target stock."""
        pass
