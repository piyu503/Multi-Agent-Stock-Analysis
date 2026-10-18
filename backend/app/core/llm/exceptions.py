"""Custom exception hierarchy for LLM providers."""


class LLMError(Exception):
    """Base exception for all LLM provider errors."""

    def __init__(self, message: str, provider: str = "unknown") -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider


class LLMConnectionError(LLMError):
    """Raised when the LLM service (e.g. Ollama daemon) cannot be reached."""


class LLMModelNotFoundError(LLMError):
    """Raised when the configured model is not installed or available on the provider."""


class LLMTimeoutError(LLMError):
    """Raised when an inference request exceeds the configured timeout."""


class LLMParsingError(LLMError):
    """Raised when the model output cannot be parsed into the expected JSON or validated schema."""

    def __init__(self, message: str, raw_output: str = "", provider: str = "unknown") -> None:
        super().__init__(message, provider=provider)
        self.raw_output = raw_output


class LLMConfigurationError(LLMError):
    """Raised when provider configuration or credentials are missing or invalid."""
