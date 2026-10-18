"""Optional Google Gemini LLM provider implementation."""

import json
from typing import Any, Dict, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from app.core.llm.base import BaseLLMProvider
from app.core.llm.exceptions import (
    LLMConfigurationError,
    LLMError,
    LLMParsingError,
    LLMTimeoutError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


class GeminiProvider(BaseLLMProvider):
    """Optional Google Gemini provider using the standard Gemini REST API.

    Safety:
    - Disabled unless explicitly configured via LLM_PROVIDER=gemini and GEMINI_API_KEY.
    - Never automatically invoked as a fallback when Ollama is selected.
    - Secrets and API keys are never logged.
    """

    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.0-flash",
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(model_name=model_name, provider_name="gemini")
        if not api_key:
            raise LLMConfigurationError(
                "Gemini provider is selected but 'GEMINI_API_KEY' is not set. "
                "Provide a valid key or switch to local Ollama via LLM_PROVIDER=ollama.",
                provider="gemini",
            )
        self.api_key = api_key
        self.timeout = timeout_seconds

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generate raw text response via Gemini generateContent endpoint."""
        url = f"{self.API_BASE}/{self.model_name}:generateContent?key={self.api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTION: {system_prompt}"}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }

        return await self._send_request(url, payload)

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        """Generate structured response validated against Pydantic schema using Gemini responseSchema."""
        url = f"{self.API_BASE}/{self.model_name}:generateContent?key={self.api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTION: {system_prompt}"}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }

        raw_text = await self._send_request(url, payload)
        try:
            parsed = json.loads(raw_text)
            return response_model.model_validate(parsed)
        except json.JSONDecodeError as e:
            raise LLMParsingError("Gemini did not return valid JSON.", raw_output=raw_text[:300], provider="gemini") from e
        except ValidationError as e:
            raise LLMParsingError(
                f"Gemini response did not conform to schema '{response_model.__name__}': {str(e)}",
                raw_output=raw_text[:300],
                provider="gemini",
            ) from e

    async def check_health(self) -> Dict[str, Any]:
        """Verify API key validity without running expensive inference."""
        return {
            "status": "configured" if self.api_key else "unconfigured",
            "provider": self.provider_name,
            "configured_model": self.model_name,
            "has_api_key": bool(self.api_key),
        }

    async def _send_request(self, url: str, payload: Dict[str, Any]) -> str:
        """Send HTTP request with timeout and masked error logging."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    logger.error(f"Gemini API returned HTTP {resp.status_code}")
                    raise LLMError(f"Gemini API error (HTTP {resp.status_code})", provider=self.provider_name)
                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise LLMError("Gemini returned no response candidates.", provider=self.provider_name)
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise LLMError("Gemini response contained no content parts.", provider=self.provider_name)
                return parts[0].get("text", "")
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"Gemini request timed out after {self.timeout}s.", provider=self.provider_name) from e
        except httpx.RequestError as e:
            raise LLMError(f"Network error while contacting Gemini: {str(e)}", provider=self.provider_name) from e
