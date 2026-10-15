from fastapi import APIRouter
from app.api.v1.analysis import router as analysis_router
from app.api.v1.health import router as health_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(analysis_router)
