from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app_main.config import load_config
from app_main.core.assets import MODEL_EXTENSIONS, MODEL_PREVIEW_EXTENSIONS, MODEL_SUPPORT_EXTENSIONS, classify_for_source
from app_main.core.db import session
from app_main.core.metadata import read_metadata


def sync_config_sources() -> None:
    for source in load_config().sources:
        add_source(source.name, str(source.path), list(source.kinds))


def list_sources() -> list[dict]:
    sync_config_sources()
    with session() as conn:
        rows = conn.execute(
            """
            SELECT id, name, path, enabled, kinds, exclude, last_scan_at, last_scan_summary
            FROM sources
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()
    return [_source_dict(row) for row in rows]


def add_source(name: str, path: str, kinds: list[str] | None = None) -> dict:
    source_path = str(Path(path).expanduser().resolve())
    display_name = name.strip() or Path(source_path).name or source_path
    kinds_value = ",".join(kinds or ["model", "audio", "image"])
    with session() as conn:
        conn.execute(
            """
            INSERT INTO sources(name, path, kinds)
            VALUES (?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET name = excluded.name, kinds = excluded.kinds, enabled = 1
            """,
            (display_name, source_path, kinds_value),
        )
        row = conn.execute("SELECT * FROM sources WHERE path = ?", (source_path,)).fetchone()
    return _source_dict(row)


def delete_source(source_id: int) -> None:
    with session() as conn:
        conn.execute("DELETE FROM sources WHERE id = ?", (source_id,))


def scan_source(source_id: int) -> dict:
    now = _now()
    with session() as conn:
        source = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        if not source:
            return {"source_id": source_id, "added": 0, "updated": 0, "missing": 0, "error": "source not found"}

        root = Path(source["path"])
        if not root.is_dir():
            summary = {"added": 0, "updated": 0, "missing": 0, "error": "source path is not accessible"}
            conn.execute(
                "UPDATE sources SET last_scan_at = ?, last_scan_summary = ? WHERE id = ?",
                (now, json.dumps(summary, ensure_ascii=False), source_id),
            )
            return summary

        allowed = set((source["kinds"] or "").split(","))
        if allowed == {"model"}:
            return _scan_model_packages(conn, source, root, now)

        seen: set[str] = set()
        added = 0
        updated = 0
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            classified = classify_for_source(path, allowed)
            if not classified:
                continue
            kind, file_format = classified
            relative = path.relative_to(root).as_posix()
            seen.add(relative)
            stat = path.stat()
            metadata, error = read_metadata(path, kind)
            existing = conn.execute(
                "SELECT id, size, mtime FROM assets WHERE source_id = ? AND relative_path = ?",
                (source_id, relative),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE assets
                    SET name = ?, kind = ?, format = ?, size = ?, mtime = ?, status = 'active',
                        metadata = ?, error = ?, scanned_at = ?
                    WHERE id = ?
                    """,
                    (
                        path.name,
                        kind,
                        file_format,
                        stat.st_size,
                        stat.st_mtime,
                        json.dumps(metadata, ensure_ascii=False),
                        error,
                        now,
                        existing["id"],
                    ),
                )
                updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO assets(
                        source_id, relative_path, name, kind, format, size, mtime,
                        status, metadata, error, scanned_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                    """,
                    (
                        source_id,
                        relative,
                        path.name,
                        kind,
                        file_format,
                        stat.st_size,
                        stat.st_mtime,
                        json.dumps(metadata, ensure_ascii=False),
                        error,
                        now,
                    ),
                )
                added += 1

        existing_paths = {
            row["relative_path"]
            for row in conn.execute("SELECT relative_path FROM assets WHERE source_id = ?", (source_id,))
        }
        missing_paths = existing_paths - seen
        for relative in missing_paths:
            conn.execute(
                "UPDATE assets SET status = 'missing', scanned_at = ? WHERE source_id = ? AND relative_path = ?",
                (now, source_id, relative),
            )

        summary = {"source_id": source_id, "added": added, "updated": updated, "missing": len(missing_paths)}
        conn.execute(
            "UPDATE sources SET last_scan_at = ?, last_scan_summary = ? WHERE id = ?",
            (now, json.dumps(summary, ensure_ascii=False), source_id),
        )
        return summary


def scan_all_sources() -> dict:
    summaries = []
    for source in list_sources():
        if source["enabled"]:
            summaries.append(scan_source(source["id"]))
    return {
        "sources": summaries,
        "added": sum(item.get("added", 0) for item in summaries),
        "updated": sum(item.get("updated", 0) for item in summaries),
        "missing": sum(item.get("missing", 0) for item in summaries),
    }


def _scan_model_packages(conn, source, root: Path, now: str) -> dict:
    source_id = source["id"]
    packages = _model_packages(root)
    seen: set[str] = set()
    added = 0
    updated = 0

    for package_dir, files in packages.items():
        primary = _choose_model_primary(files, package_dir)
        if primary is None:
            continue

        relative = primary.relative_to(root).as_posix()
        seen.add(relative)
        stat = primary.stat()
        metadata, error = read_metadata(primary, "model")
        metadata.update(
            {
                "package_dir": "." if package_dir == root else package_dir.relative_to(root).as_posix(),
                "package_files": len(files),
                "support_files": max(0, len(files) - 1),
            }
        )
        existing = conn.execute(
            "SELECT id, size, mtime FROM assets WHERE source_id = ? AND relative_path = ?",
            (source_id, relative),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE assets
                SET name = ?, kind = 'model', format = ?, size = ?, mtime = ?, status = 'active',
                    metadata = ?, error = ?, scanned_at = ?
                WHERE id = ?
                """,
                (
                    primary.stem,
                    primary.suffix.lower().lstrip(".") or "file",
                    stat.st_size,
                    stat.st_mtime,
                    json.dumps(metadata, ensure_ascii=False),
                    error,
                    now,
                    existing["id"],
                ),
            )
            updated += 1
        else:
            conn.execute(
                """
                INSERT INTO assets(
                    source_id, relative_path, name, kind, format, size, mtime,
                    status, metadata, error, scanned_at
                )
                VALUES (?, ?, ?, 'model', ?, ?, ?, 'active', ?, ?, ?)
                """,
                (
                    source_id,
                    relative,
                    primary.stem,
                    primary.suffix.lower().lstrip(".") or "file",
                    stat.st_size,
                    stat.st_mtime,
                    json.dumps(metadata, ensure_ascii=False),
                    error,
                    now,
                ),
            )
            added += 1

    existing_paths = {
        row["relative_path"]
        for row in conn.execute("SELECT relative_path FROM assets WHERE source_id = ?", (source_id,))
    }
    missing_paths = existing_paths - seen
    for relative in missing_paths:
        conn.execute(
            "UPDATE assets SET status = 'missing', scanned_at = ? WHERE source_id = ? AND relative_path = ?",
            (now, source_id, relative),
        )

    summary = {"source_id": source_id, "added": added, "updated": updated, "missing": len(missing_paths)}
    conn.execute(
        "UPDATE sources SET last_scan_at = ?, last_scan_summary = ? WHERE id = ?",
        (now, json.dumps(summary, ensure_ascii=False), source_id),
    )
    return summary


def _model_packages(root: Path) -> dict[Path, list[Path]]:
    packages: dict[Path, list[Path]] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in MODEL_SUPPORT_EXTENSIONS or suffix in MODEL_EXTENSIONS or suffix not in {""}:
            packages.setdefault(_model_package_root(root, path), []).append(path)
    return packages


def _model_package_root(root: Path, path: Path) -> Path:
    relative_parts = path.relative_to(root).parts
    for index, part in enumerate(relative_parts[:-1]):
        if part.lower().endswith(".package"):
            return root.joinpath(*relative_parts[: index + 1])
    return path.parent


def _choose_model_primary(files: list[Path], package_dir: Path | None = None) -> Path | None:
    candidates = [
        path
        for path in files
        if path.suffix.lower() in MODEL_EXTENSIONS or path.suffix.lower() not in MODEL_SUPPORT_EXTENSIONS
    ]
    if not candidates:
        return None

    meta_primary = _meta_primary_model(package_dir)
    if meta_primary:
        for path in candidates:
            if path.name.lower() == meta_primary.lower():
                return path

    def priority(path: Path) -> tuple[int, str]:
        suffix = path.suffix.lower()
        if suffix in MODEL_PREVIEW_EXTENSIONS:
            return (0, path.name.lower())
        if suffix == ".mdx":
            return (1, path.name.lower())
        if suffix == ".mdl":
            return (2, path.name.lower())
        if suffix in MODEL_EXTENSIONS:
            return (3, path.name.lower())
        return (4, path.name.lower())

    return sorted(candidates, key=priority)[0]


def _meta_primary_model(package_dir: Path | None) -> str:
    if package_dir is None:
        return ""
    meta_path = package_dir / "meta.json"
    if not meta_path.is_file():
        return ""
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return ""
    source_path = str(data.get("source_path") or "").replace("\\", "/").split("/")[-1]
    if source_path.lower().endswith(tuple(MODEL_EXTENSIONS)):
        return source_path
    for item in data.get("md5_file_list") or []:
        name = str(item).replace("\\", "/").split("/")[-1]
        if name.lower().endswith(tuple(MODEL_EXTENSIONS)):
            return name
    return ""


def _source_dict(row) -> dict:
    summary = row["last_scan_summary"] or ""
    return {
        "id": row["id"],
        "name": row["name"],
        "path": row["path"],
        "enabled": bool(row["enabled"]),
        "kinds": [item for item in (row["kinds"] or "").split(",") if item],
        "exclude": row["exclude"],
        "last_scan_at": row["last_scan_at"],
        "last_scan_summary": json.loads(summary) if summary else {},
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
