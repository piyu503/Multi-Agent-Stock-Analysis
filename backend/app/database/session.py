from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """Return the singleton AsyncEngine instance, creating it if necessary."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.DATABASE_URL

        # Normalize postgres driver for asyncpg
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Connection options tailored for async engine
        is_sqlite = "sqlite" in db_url
        engine_args = {
            "echo": settings.DEBUG,
            "future": True,
        }

        if not is_sqlite:
            engine_args.update(
                {
                    "pool_size": settings.DATABASE_POOL_SIZE,
                    "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                    "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
                    "pool_pre_ping": True,
                    "connect_args": {
                        "command_timeout": settings.DATABASE_CONNECT_TIMEOUT,
                        "timeout": settings.DATABASE_CONNECT_TIMEOUT,
                    },
                }
            )

        _engine = create_async_engine(db_url, **engine_args)
        logger.info(f"Database engine initialized for: {db_url.split('@')[-1] if '@' in db_url else 'local'}")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the singleton session factory."""
    global _session_maker
    if _session_maker is None:
        engine = get_engine()
        _session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for injecting transactional async database sessions."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db_engine() -> None:
    """Dispose of the database engine connection pool on shutdown."""
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_maker = None
        logger.info("Database connection pool disposed.")
