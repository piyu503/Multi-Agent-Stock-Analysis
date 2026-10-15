from contextlib import asynccontextmanager
import time
import uuid
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.health import check_health
from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.database.session import close_db_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown hooks."""
    setup_logging()
    settings = get_settings()
    logger.info(
        f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]"
    )
    yield
    logger.info("Shutting down application and disposing resources...")
    await close_db_engine()
    logger.info("Application shutdown complete.")


def create_app() -> FastAPI:
    """FastAPI application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" or settings.DEBUG else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" or settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" or settings.DEBUG else None,
    )

    # 1. Register Exception Handlers
    register_exception_handlers(app)

    # 2. CORS Middleware - restricted to configured frontend origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # 3. Request timing & tracing middleware
    @app.middleware("http")
    async def add_process_time_and_request_id(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000.0
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        return response

    # 4. Include Routers
    app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)

    # Direct convenience endpoint /api/health pointing to the same health check
    app.add_api_route(
        "/api/health",
        check_health,
        methods=["GET"],
        tags=["Health"],
        summary="Root Health Endpoint (Convenience Alias)",
        include_in_schema=False,
    )

    # Root summary route
    @app.get("/", tags=["Root"], include_in_schema=False)
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": "/docs" if settings.ENVIRONMENT != "production" else "disabled in production",
            "health": f"{settings.API_V1_PREFIX}/health",
        }

    return app


app = create_app()
