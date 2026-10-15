from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Normalized output from a financial analysis tool."""
    success: bool
    data: Optional[Any] = None
    source: str
    cached: bool = False
    error: Optional[str] = None


class BaseFinancialTool(ABC):
    """Abstract Base Class for external data integrations and financial computation tools."""

    name: str
    description: str

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool operation asynchronously."""
        pass
