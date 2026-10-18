"""Unit tests for LLM provider abstraction, Ollama provider, Gemini provider, and factory."""

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from pydantic import BaseModel

from app.core.config import Settings
from app.core.llm.base import BaseLLMProvider
from app.core.llm.exceptions import (
    LLMConfigurationError,
    LLMConnectionError,
    LLMError,
    LLMModelNotFoundError,
    LLMParsingError,
    LLMTimeoutError,
)
from app.core.llm.factory import get_llm_provider
from app.core.llm.gemini import GeminiProvider
from app.core.llm.ollama import OllamaProvider


class DummySchema(BaseModel):
    summary: str
    score: int


class TestLLMFactory:
    def test_factory_defaults_to_ollama(self):
        settings = Settings()
        provider = get_llm_provider(settings)
        assert isinstance(provider, OllamaProvider)
        assert provider.provider_name == "ollama"
        assert provider.model_name == "deepseek-r1:7b"
        assert provider.base_url == "http://localhost:11434"

    def test_factory_selects_gemini_when_explicitly_configured(self):
        settings = Settings(
            LLM_PROVIDER="gemini",
            GEMINI_API_KEY="test-mock-key",
            GEMINI_MODEL="gemini-2.0-flash",
        )
        provider = get_llm_provider(settings)
        assert isinstance(provider, GeminiProvider)
        assert provider.provider_name == "gemini"
        assert provider.model_name == "gemini-2.0-flash"

    def test_factory_raises_when_gemini_selected_without_key(self):
        settings = Settings(LLM_PROVIDER="gemini", GEMINI_API_KEY=None)
        with pytest.raises(LLMConfigurationError) as exc_info:
            get_llm_provider(settings)
        assert "GEMINI_API_KEY" in str(exc_info.value)

    def test_factory_rejects_unsupported_provider(self):
        settings = Settings()
        settings.LLM_PROVIDER = "unsupported_xyz"  # type: ignore
        with pytest.raises(LLMConfigurationError) as exc_info:
            get_llm_provider(settings)
        assert "Unsupported LLM provider" in str(exc_info.value)


class TestOllamaProvider:
    @pytest.mark.asyncio
    async def test_strip_thinking_tags_from_deepseek_r1(self):
        """Verify that DeepSeek R1 <think>...</think> blocks are stripped."""
        raw_text = (
            "<think>\n"
            "Here is my internal reasoning about the financial numbers.\n"
            "Close is 2465.0 and SMA-20 is 2143.0.\n"
            "</think>\n"
            '{"summary": "Bullish trend above 20-SMA", "score": 85}'
        )
        cleaned = OllamaProvider._strip_thinking_tags(raw_text)
        assert "<think>" not in cleaned
        assert "</think>" not in cleaned
        assert '{"summary": "Bullish trend above 20-SMA", "score": 85}' == cleaned

    @pytest.mark.asyncio
    async def test_bounded_json_parsing_direct(self):
        provider = OllamaProvider()
        result = provider._parse_json_bounded('{"summary": "ok", "score": 10}')
        assert result == {"summary": "ok", "score": 10}

    @pytest.mark.asyncio
    async def test_bounded_json_parsing_markdown_fence(self):
        provider = OllamaProvider()
        result = provider._parse_json_bounded('```json\n{"summary": "fenced", "score": 20}\n```')
        assert result == {"summary": "fenced", "score": 20}

    @pytest.mark.asyncio
    async def test_bounded_json_parsing_embedded_in_preamble(self):
        provider = OllamaProvider()
        result = provider._parse_json_bounded('Here is the requested output:\n{"summary": "preamble", "score": 30}\nEnd of response.')
        assert result == {"summary": "preamble", "score": 30}

    @pytest.mark.asyncio
    async def test_unparseable_output_raises_llm_parsing_error(self):
        provider = OllamaProvider()
        with pytest.raises(LLMParsingError):
            provider._parse_json_bounded("This is pure text with no JSON whatsoever.")

    @pytest.mark.asyncio
    async def test_generate_structured_success_with_mocked_http(self):
        provider = OllamaProvider(model_name="deepseek-r1:7b")
        mock_response = httpx.Response(
            status_code=200,
            json={
                "message": {
                    "role": "assistant",
                    "content": "<think>Processing</think>{\"summary\": \"Structured analysis\", \"score\": 90}",
                }
            },
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            result = await provider.generate_structured("Analyze this", DummySchema)
            assert isinstance(result, DummySchema)
            assert result.summary == "Structured analysis"
            assert result.score == 90

    @pytest.mark.asyncio
    async def test_ollama_not_running_raises_connection_error_without_cloud_fallback(self):
        provider = OllamaProvider(base_url="http://localhost:11434")

        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.generate("Hello")
            assert "Cannot connect to local Ollama daemon" in str(exc_info.value)
            assert exc_info.value.provider == "ollama"

    @pytest.mark.asyncio
    async def test_ollama_model_not_found_raises_model_not_found_error(self):
        provider = OllamaProvider(model_name="nonexistent-model:xyz")
        mock_response = httpx.Response(
            status_code=404,
            text='{"error": "model \'nonexistent-model:xyz\' not found"}',
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            with pytest.raises(LLMModelNotFoundError) as exc_info:
                await provider.generate("Hello")
            assert "was not found in Ollama" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ollama_timeout_raises_llm_timeout_error(self):
        provider = OllamaProvider(timeout_seconds=2.0)

        with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
            with pytest.raises(LLMTimeoutError) as exc_info:
                await provider.generate("Hello")
            assert "timed out after" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_health_when_reachable(self):
        provider = OllamaProvider(model_name="deepseek-r1:7b")
        mock_response = httpx.Response(
            status_code=200,
            json={"models": [{"name": "deepseek-r1:7b:latest"}, {"name": "qwen3:8b"}]},
        )

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            health = await provider.check_health()
            assert health["status"] == "ok"
            assert health["model_installed"] is True
            assert "deepseek-r1:7b:latest" in health["available_models"]

    @pytest.mark.asyncio
    async def test_check_health_when_unreachable(self):
        provider = OllamaProvider()
        with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("Connection refused")):
            health = await provider.check_health()
            assert health["status"] == "unreachable"
            assert health["provider"] == "ollama"
