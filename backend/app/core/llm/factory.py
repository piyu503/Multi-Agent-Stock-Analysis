"""Factory for selecting and instantiating the configured LLM provider."""

from typing import Optional
from app.core.config import Settings, get_settings
from app.core.llm.base import BaseLLMProvider
from app.core.llm.exceptions import LLMConfigurationError
from app.core.llm.gemini import GeminiProvider
from app.core.llm.ollama import OllamaProvider


def get_llm_provider(settings: Optional[Settings] = None) -> BaseLLMProvider:
    """Instantiate and return the configured LLM provider.

    Guarantees:
    - Defaults to local Ollama.
    - Does not instantiate Gemini or verify Gemini credentials unless explicitly configured.
    - No silent cloud fallback if local Ollama fails.
    """
    cfg = settings or get_settings()

    provider_name = (cfg.LLM_PROVIDER or "ollama").strip().lower()

    if provider_name == "ollama":
        return OllamaProvider(
            model_name=cfg.OLLAMA_MODEL,
            base_url=cfg.OLLAMA_BASE_URL,
            timeout_seconds=cfg.OLLAMA_TIMEOUT_SECONDS,
        )
    elif provider_name == "gemini":
        return GeminiProvider(
            api_key=cfg.GEMINI_API_KEY,
            model_name=cfg.GEMINI_MODEL,
        )
    else:
        raise LLMConfigurationError(
            f"Unsupported LLM provider '{cfg.LLM_PROVIDER}'. Supported providers are: 'ollama', 'gemini'.",
            provider=cfg.LLM_PROVIDER,
        )
