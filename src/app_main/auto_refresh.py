from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from app_main.config import AutoRefreshConfig
from app_main.core.assets import MODEL_SUPPORT_EXTENSIONS, classify_for_source
from app_main.core.sources import list_sources, scan_source

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceSignature:
    file_count: int
    latest_mtime_ns: int
    total_size: int


async def auto_refresh_loop(config: AutoRefreshConfig) -> None:
    signatures: dict[int, SourceSignature | None] = {}

    if config.initial_scan:
        await asyncio.to_thread(_scan_changed_sources, signatures, force=True)
    else:
        signatures.update(await asyncio.to_thread(_current_signatures))

    while True:
        await asyncio.sleep(config.interval_seconds)
        await asyncio.to_thread(_scan_changed_sources, signatures, force=False)


def _scan_changed_sources(signatures: dict[int, SourceSignature | None], *, force: bool) -> None:
    for source in list_sources():
        if not source["enabled"]:
            continue

        source_id = source["id"]
        signature = _source_signature(Path(source["path"]), set(source["kinds"]))
        previous = signatures.get(source_id)
        if not force and previous == signature:
            logger.debug("auto_refresh_unchanged source_id=%s path=%s", source_id, source["path"])
            continue

        logger.info("Auto refresh scanning source=%s path=%s", source["name"], source["path"])
        summary = scan_source(source_id)
        signatures[source_id] = signature
        logger.info(
            "Auto refresh finished source=%s added=%s updated=%s missing=%s error=%s",
            source["name"],
            summary.get("added", 0),
            summary.get("updated", 0),
            summary.get("missing", 0),
            summary.get("error", ""),
        )


def _current_signatures() -> dict[int, SourceSignature | None]:
    signatures: dict[int, SourceSignature | None] = {}
    for source in list_sources():
        if source["enabled"]:
            signatures[source["id"]] = _source_signature(Path(source["path"]), set(source["kinds"]))
    return signatures


def _source_signature(root: Path, allowed_kinds: set[str]) -> SourceSignature | None:
    if not root.is_dir():
        return None

    file_count = 0
    latest_mtime_ns = 0
    total_size = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if allowed_kinds == {"model"} and path.suffix.lower() in MODEL_SUPPORT_EXTENSIONS:
            classified = ("model-support", path.suffix.lower().lstrip("."))
        else:
            classified = classify_for_source(path, allowed_kinds)
        if not classified:
            continue

        try:
            stat = path.stat()
        except OSError:
            continue

        file_count += 1
        latest_mtime_ns = max(latest_mtime_ns, stat.st_mtime_ns)
        total_size += stat.st_size

    return SourceSignature(file_count=file_count, latest_mtime_ns=latest_mtime_ns, total_size=total_size)
