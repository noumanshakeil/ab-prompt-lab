from fastapi import APIRouter
from backend.api import health, experiments, ui
api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(experiments.router, prefix="/api", tags=["experiments"])
api_router.include_router(ui.router, tags=["ui"])
