from functools import lru_cache
from typing import List, Literal, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Application Settings
    PROJECT_NAME: str = "Multi-Agent Stock Analysis Platform"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security & CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"]
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: object) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v  # type: ignore
        raise ValueError(v)

    # Database Settings (PostgreSQL async default)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/stock_analysis"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_CONNECT_TIMEOUT: float = 3.0  # seconds

    # Supabase Auth Configuration (Future Phase)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # LLM Provider Configuration (Future Phase)
    LLM_PROVIDER: str = "gemini"  # "gemini" | "openai" | "anthropic" | "local"
    GEMINI_API_KEY: Optional[str] = None


@lru_cache()
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
