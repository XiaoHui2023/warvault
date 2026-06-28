from __future__ import annotations

import mimetypes

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app_main.core.assets import get_asset, list_assets, resolve_asset_file, resolve_asset_related_file, update_asset

router = APIRouter(prefix="/assets", tags=["assets"])


class AssetUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    favorite: bool = False


@router.get("")
def get_assets(
    kind: str | None = None,
    source_id: int | None = None,
    q: str | None = None,
    tag: str | None = None,
    limit: int = Query(default=200, ge=1, le=1000),
) -> list[dict]:
    return list_assets(kind=kind, source_id=source_id, query=q, tag=tag, limit=limit)


@router.get("/{asset_id}")
def get_asset_detail(asset_id: int) -> dict:
    asset = get_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.patch("/{asset_id}")
def patch_asset(asset_id: int, payload: AssetUpdate) -> dict:
    asset = update_asset(
        asset_id,
        tags=payload.tags,
        description=payload.description,
        favorite=payload.favorite,
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.get("/{asset_id}/file")
def asset_file(asset_id: int):
    path = resolve_asset_file(asset_id)
    if not path:
        raise HTTPException(status_code=404, detail="Asset file not found")
    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=media_type)


@router.get("/{asset_id}/related/{relative_path:path}")
def asset_related_file(asset_id: int, relative_path: str):
    path = resolve_asset_related_file(asset_id, relative_path)
    if not path:
        raise HTTPException(status_code=404, detail="Related asset file not found")
    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=media_type)


@router.get("/{asset_id}/{relative_path:path}")
def asset_loader_relative_file(asset_id: int, relative_path: str):
    path = resolve_asset_related_file(asset_id, relative_path)
    if not path:
        raise HTTPException(status_code=404, detail="Related asset file not found")
    media_type, _ = mimetypes.guess_type(path.name)
    return FileResponse(path, media_type=media_type)
