from __future__ import annotations

from fastapi import APIRouter

from app_main.core.db import init_db
from app_main.core.paths import database_path

router = APIRouter(tags=["status"])


@router.get("/status")
def status() -> dict:
    init_db()
    return {
        "name": "warvault",
        "version": "0.0.0",
        "database": str(database_path()),
    }
