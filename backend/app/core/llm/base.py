"""Abstract base class definition for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(ABC):
    """Abstract interface defining standard methods for LLM inference and structured validation."""

    def __init__(self, model_name: str, provider_name: str) -> None:
        self.model_name = model_name
        self.provider_name = provider_name

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generate a raw text response for the given prompt."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        """Generate and validate a structured response matching the specified Pydantic model."""
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Perform a non-invasive diagnostic health check for provider availability and model presence."""
        pass
