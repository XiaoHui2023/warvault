from __future__ import annotations

from fastapi import APIRouter

from app_main.api.assets import router as assets_router
from app_main.api.sources import router as sources_router
from app_main.api.status import router as status_router

router = APIRouter(prefix="/api")
router.include_router(status_router)
router.include_router(sources_router)
router.include_router(assets_router)
