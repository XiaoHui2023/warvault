from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from app_main.core.sources import add_source, delete_source, list_sources, scan_all_sources, scan_source

router = APIRouter(prefix="/sources", tags=["sources"])


class SourceCreate(BaseModel):
    name: str = ""
    path: str
    kinds: list[str] = Field(default_factory=lambda: ["model", "audio", "image"])


@router.get("")
def get_sources() -> list[dict]:
    return list_sources()


@router.post("")
def create_source(payload: SourceCreate) -> dict:
    return add_source(payload.name, payload.path, payload.kinds)


@router.delete("/{source_id}")
def remove_source(source_id: int) -> dict:
    delete_source(source_id)
    return {"ok": True}


@router.post("/{source_id}/scan")
def scan_single_source(source_id: int) -> dict:
    summary = scan_source(source_id)
    if summary.get("error") == "source not found":
        raise HTTPException(status_code=404, detail="Source not found")
    return summary


@router.post("/scan")
def scan_sources() -> dict:
    return scan_all_sources()
