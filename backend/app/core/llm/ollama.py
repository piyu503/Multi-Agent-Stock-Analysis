"""Ollama local LLM provider implementation."""

import json
import re
from typing import Any, Dict, List, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from app.core.llm.base import BaseLLMProvider
from app.core.llm.exceptions import (
    LLMConnectionError,
    LLMError,
    LLMModelNotFoundError,
    LLMParsingError,
    LLMTimeoutError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


class OllamaProvider(BaseLLMProvider):
    """Local LLM provider interfacing with Ollama REST API.

    Features:
    - Async non-blocking HTTP requests via httpx.
    - DeepSeek-R1 <think>...</think> reasoning tag stripping.
    - Bounded JSON extraction and Pydantic validation.
    - Non-invasive diagnostic health checking.
    """

    def __init__(
        self,
        model_name: str = "deepseek-r1:7b",
        base_url: str = "http://localhost:11434",
        timeout_seconds: float = 90.0,
    ) -> None:
        super().__init__(model_name=model_name, provider_name="ollama")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generate raw text response via Ollama chat endpoint."""
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 1500},
        }

        raw_response = await self._send_chat_request(payload)
        return self._strip_thinking_tags(raw_response)

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        """Generate structured response, parse JSON, and validate against Pydantic schema."""
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        augmented_system = (
            (system_prompt + "\n\n" if system_prompt else "")
            + "You must respond with a JSON object populated with concrete analysis values matching this schema:\n"
            + schema_json
            + "\nCRITICAL: Output only the final JSON object with values. Do not output meta-schema keywords or wrap fields in a 'properties' dictionary."
        )

        messages = [
            {"role": "system", "content": augmented_system},
            {"role": "user", "content": prompt},
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature, "num_predict": 1024},
        }

        raw_text = await self._send_chat_request(payload)
        cleaned_text = self._strip_thinking_tags(raw_text)

        # Bounded JSON extraction and validation
        parsed_dict = self._parse_json_bounded(cleaned_text)

        # Bounded repair: If local LLM mirrored schema structure by placing fields under "properties"
        if isinstance(parsed_dict, dict) and "properties" in parsed_dict and isinstance(parsed_dict["properties"], dict):
            # If trend_interpretation or other model fields are in properties, unwrap it
            parsed_dict = parsed_dict["properties"]

        # Bounded normalization: If list-of-strings fields contain dictionary objects, flatten them cleanly
        parsed_dict = self._normalize_json_dict(parsed_dict)

        try:
            return response_model.model_validate(parsed_dict)
        except ValidationError as e:
            logger.error(f"Pydantic schema validation error against {response_model.__name__}: {e}")
            raise LLMParsingError(
                f"Model response did not conform to schema '{response_model.__name__}': {str(e)}",
                raw_output=cleaned_text[:500],
                provider=self.provider_name,
            ) from e

    async def check_health(self) -> Dict[str, Any]:
        """Verify Ollama service is reachable and check model presence without running inference."""
        url = f"{self.base_url}/api/tags"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    # Check exact or normalized model match (e.g. "deepseek-r1:7b" or "deepseek-r1:7b:latest")
                    model_found = any(
                        m == self.model_name or m.startswith(f"{self.model_name}:") or self.model_name.startswith(m)
                        for m in models
                    )
                    return {
                        "status": "ok" if model_found else "degraded",
                        "provider": self.provider_name,
                        "base_url": self.base_url,
                        "configured_model": self.model_name,
                        "model_installed": model_found,
                        "available_models": models,
                    }
                return {
                    "status": "error",
                    "provider": self.provider_name,
                    "base_url": self.base_url,
                    "configured_model": self.model_name,
                    "message": f"Ollama HTTP {resp.status_code}",
                }
        except httpx.ConnectError:
            return {
                "status": "unreachable",
                "provider": self.provider_name,
                "base_url": self.base_url,
                "configured_model": self.model_name,
                "message": f"Cannot connect to Ollama daemon at {self.base_url}. Ensure Ollama is running.",
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": self.provider_name,
                "base_url": self.base_url,
                "configured_model": self.model_name,
                "message": f"Diagnostic check failed: {str(e)}",
            }

    async def _send_chat_request(self, payload: Dict[str, Any]) -> str:
        """Internal helper to send chat request with bounded timeout and safe error translation."""
        url = f"{self.base_url}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 404:
                    err_text = response.text
                    if "not found" in err_text.lower():
                        raise LLMModelNotFoundError(
                            f"Configured model '{self.model_name}' was not found in Ollama. "
                            f"Run 'ollama pull {self.model_name}' to install it.",
                            provider=self.provider_name,
                        )
                    raise LLMError(f"Ollama returned 404 Not Found: {err_text}", provider=self.provider_name)

                if response.status_code != 200:
                    raise LLMError(
                        f"Ollama API returned HTTP {response.status_code}: {response.text[:300]}",
                        provider=self.provider_name,
                    )

                data = response.json()
                message = data.get("message", {})
                content = message.get("content", "")
                if not content:
                    raise LLMError("Ollama returned an empty response.", provider=self.provider_name)
                return content

        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Ollama at {self.base_url}: {e}")
            raise LLMConnectionError(
                f"Cannot connect to local Ollama daemon at {self.base_url}. "
                "Ensure Ollama is running locally ('ollama serve').",
                provider=self.provider_name,
            ) from e
        except httpx.TimeoutException as e:
            logger.error(f"Ollama inference timed out after {self.timeout}s: {e}")
            raise LLMTimeoutError(
                f"Local model '{self.model_name}' timed out after {self.timeout}s. "
                "The system may be under heavy load.",
                provider=self.provider_name,
            ) from e

    @staticmethod
    def _strip_thinking_tags(text: str) -> str:
        """Strip DeepSeek R1 reasoning tags: <think>...</think>."""
        # Use re.DOTALL so .* matches newlines
        cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        return cleaned.strip()

    def _parse_json_bounded(self, text: str) -> Dict[str, Any]:
        """Bounded repair strategy to extract and parse JSON from model output."""
        cleaned = text.strip()
        if not cleaned:
            raise LLMParsingError("Model output was empty after stripping reasoning tags.", raw_output=text)

        # 1. Direct parse attempt
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 2. Markdown fence extraction (```json ... ``` or ``` ... ```)
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # 3. Outer brace extraction: first '{' to last '}'
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            substring = cleaned[start_idx : end_idx + 1]
            try:
                return json.loads(substring)
            except json.JSONDecodeError:
                pass

        # If all bounded strategies fail, raise structured exception without infinite retries
        logger.warning(f"Failed to parse JSON from model output: {cleaned[:200]}...")
        raise LLMParsingError(
            "Could not parse valid JSON from model response.",
            raw_output=cleaned[:500],
            provider=self.provider_name,
        )

    @staticmethod
    def _normalize_json_dict(data: Any) -> Any:
        """Bounded repair to normalize dict structures where models return object items for string list fields."""
        if not isinstance(data, dict):
            return data

        normalized: Dict[str, Any] = {}
        for key, val in data.items():
            if isinstance(val, list):
                cleaned_items = []
                for item in val:
                    if isinstance(item, str):
                        if not item.strip().startswith('{"type":'):
                            cleaned_items.append(item)
                    elif isinstance(item, dict):
                        # Skip pure schema artifacts e.g. {"type": "string"}
                        if set(item.keys()).issubset({"type"}) or item.get("type") == "string" and len(item) == 1:
                            continue
                        # Extract title/name/items/evidence or combine them into a single string
                        title = item.get("title") or item.get("name") or ""
                        items_val = item.get("items")
                        evidence_val = item.get("evidence")
                        parts = []
                        if title and title != "string":
                            parts.append(str(title))
                        if items_val:
                            if isinstance(items_val, list):
                                parts.append(", ".join(str(x) for x in items_val))
                            else:
                                parts.append(str(items_val))
                        elif evidence_val:
                            if isinstance(evidence_val, list):
                                parts.append(", ".join(str(x) for x in evidence_val))
                            else:
                                parts.append(str(evidence_val))
                        if parts:
                            cleaned_items.append(": ".join(parts) if len(parts) > 1 else parts[0])
                    else:
                        cleaned_items.append(str(item))
                normalized[key] = cleaned_items
            elif isinstance(val, dict):
                normalized[key] = OllamaProvider._normalize_json_dict(val)
            else:
                normalized[key] = val
        return normalized
