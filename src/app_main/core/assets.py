from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app_main.core.db import session

MODEL_EXTENSIONS = {
    ".mdx",
    ".mdl",
    ".fbx",
    ".obj",
    ".glb",
    ".gltf",
    ".y3model",
    ".model",
    ".mesh",
    ".vmdl",
}
MODEL_PREVIEW_EXTENSIONS = {".fbx", ".glb", ".gltf", ".obj"}
MODEL_SUPPORT_EXTENSIONS = {
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".tga",
    ".dds",
    ".blp",
    ".mtl",
    ".mat",
    ".txt",
    ".meta",
}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg"}
IMAGE_EXTENSIONS = {".blp", ".dds", ".tga", ".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True)
class AssetType:
    kind: str
    extensions: set[str]


ASSET_TYPES = (
    AssetType("model", MODEL_EXTENSIONS),
    AssetType("audio", AUDIO_EXTENSIONS),
    AssetType("image", IMAGE_EXTENSIONS),
)


def classify(path: Path) -> tuple[str, str] | None:
    suffix = path.suffix.lower()
    for asset_type in ASSET_TYPES:
        if suffix in asset_type.extensions:
            return asset_type.kind, suffix.lstrip(".")
    return None


def classify_for_source(path: Path, allowed_kinds: set[str]) -> tuple[str, str] | None:
    classified = classify(path)
    if classified:
        kind, _file_format = classified
        return classified if kind in allowed_kinds else None
    if allowed_kinds == {"model"}:
        suffix = path.suffix.lower().lstrip(".")
        return "model", suffix or "file"
    return None


def _decode_tags(value: str) -> list[str]:
    return [item for item in value.split(",") if item]


def _row_to_asset(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["metadata"] = json.loads(data.get("metadata") or "{}")
    data["tags"] = _decode_tags(data.get("tags") or "")
    data["favorite"] = bool(data.get("favorite"))
    data["preview_url"] = f"/api/assets/{data['id']}/file"
    return data


def list_assets(
    *,
    kind: str | None = None,
    source_id: int | None = None,
    query: str | None = None,
    tag: str | None = None,
    limit: int = 200,
) -> list[dict]:
    clauses = ["assets.status = 'active'"]
    params: list[object] = []
    if kind:
        clauses.append("assets.kind = ?")
        params.append(kind)
    if source_id:
        clauses.append("assets.source_id = ?")
        params.append(source_id)
    if query:
        like = f"%{query}%"
        clauses.append(
            "(assets.name LIKE ? OR assets.relative_path LIKE ? OR assets.description LIKE ? OR assets.tags LIKE ?)"
        )
        params.extend([like, like, like, like])
    if tag:
        clauses.append("(',' || assets.tags || ',') LIKE ?")
        params.append(f"%,{tag},%")

    params.append(limit)
    where = " AND ".join(clauses)
    with session() as conn:
        rows = conn.execute(
            f"""
            SELECT assets.*, sources.name AS source_name
            FROM assets
            JOIN sources ON sources.id = assets.source_id
            WHERE {where}
            ORDER BY assets.scanned_at DESC, assets.name COLLATE NOCASE
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [_row_to_asset(row) for row in rows]


def get_asset(asset_id: int) -> dict | None:
    with session() as conn:
        row = conn.execute(
            """
            SELECT assets.*, sources.name AS source_name, sources.path AS source_path
            FROM assets
            JOIN sources ON sources.id = assets.source_id
            WHERE assets.id = ?
            """,
            (asset_id,),
        ).fetchone()
    return _row_to_asset(row) if row else None


def update_asset(asset_id: int, *, tags: list[str], description: str, favorite: bool) -> dict | None:
    cleaned_tags = ",".join(sorted({tag.strip() for tag in tags if tag.strip()}))
    with session() as conn:
        conn.execute(
            """
            UPDATE assets
            SET tags = ?, description = ?, favorite = ?
            WHERE id = ?
            """,
            (cleaned_tags, description.strip(), int(favorite), asset_id),
        )
    return get_asset(asset_id)


def resolve_asset_file(asset_id: int) -> Path | None:
    asset = get_asset(asset_id)
    if not asset:
        return None
    path = Path(asset["source_path"]) / asset["relative_path"]
    try:
        path.resolve().relative_to(Path(asset["source_path"]).resolve())
    except ValueError:
        return None
    return path if path.is_file() else None


def resolve_asset_related_file(asset_id: int, relative_path: str) -> Path | None:
    asset = get_asset(asset_id)
    if not asset:
        return None

    source_root = Path(asset["source_path"]).resolve()
    asset_dir = (source_root / asset["relative_path"]).parent
    requested = relative_path.replace("\\", "/").lstrip("/")
    candidate = (asset_dir / requested).resolve()
    resolved = _safe_related_file(source_root, candidate)
    if resolved:
        return resolved

    texture_candidate = (asset_dir / "textures" / Path(requested).name).resolve()
    resolved = _safe_related_file(source_root, texture_candidate)
    if resolved:
        return resolved

    asset_file_stem = Path(asset["relative_path"]).stem
    fbm_candidate = (asset_dir / f"{asset_file_stem}.fbm" / Path(requested).name).resolve()
    resolved = _safe_related_file(source_root, fbm_candidate)
    if resolved:
        return resolved

    mapped = _resolve_y3_texture_mapping(asset_dir, requested)
    if mapped:
        resolved = _safe_related_file(source_root, mapped.resolve())
        if resolved:
            return resolved

    return None


def _safe_related_file(source_root: Path, candidate: Path) -> Path | None:
    try:
        candidate.relative_to(source_root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _resolve_y3_texture_mapping(asset_dir: Path, requested: str) -> Path | None:
    meta_path = asset_dir / "meta.json"
    if not meta_path.is_file():
        return None
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    textures = data.get("textures")
    if not isinstance(textures, dict):
        return None

    requested_key = Path(requested).with_suffix("").as_posix().lower()
    mapped_name = ""
    for key, value in textures.items():
        if str(key).replace("\\", "/").strip("/").lower() == requested_key:
            mapped_name = str(value).replace("\\", "/").strip("/")
            break
    if not mapped_name:
        return None

    direct = asset_dir / mapped_name
    if direct.is_file():
        return direct
    return asset_dir / "textures" / mapped_name
