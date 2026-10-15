from app.core.config import Settings


def test_settings_defaults():
    """Verify default configuration values."""
    settings = Settings()
    assert settings.PROJECT_NAME == "Multi-Agent Stock Analysis Platform"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.ENVIRONMENT in ["development", "staging", "production"]
    assert "http://localhost:3000" in settings.CORS_ORIGINS


def test_settings_cors_string_parsing():
    """Verify comma-separated CORS string parsing."""
    settings = Settings(CORS_ORIGINS="http://localhost:3000,http://app.example.com")
    assert "http://localhost:3000" in settings.CORS_ORIGINS
    assert "http://app.example.com" in settings.CORS_ORIGINS
    assert len(settings.CORS_ORIGINS) == 2
