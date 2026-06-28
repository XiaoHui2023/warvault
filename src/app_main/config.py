from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

_active_config_path: str | Path | None = None


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 0
    base_url: str = "/"


@dataclass(frozen=True)
class LoggingConfig:
    enabled: bool
    level: str
    root_dir: Path


@dataclass(frozen=True)
class AutoRefreshConfig:
    enabled: bool
    interval_seconds: int
    initial_scan: bool


@dataclass(frozen=True)
class PathsConfig:
    data_dir: Path
    database_path: Path
    frontend_dist: Path


@dataclass(frozen=True)
class SourceConfig:
    name: str
    path: Path
    kinds: tuple[str, ...]


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    logging: LoggingConfig
    auto_refresh: AutoRefreshConfig
    paths: PathsConfig
    sources: tuple[SourceConfig, ...]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config_path() -> Path:
    return Path.cwd() / "config.yaml"


def set_config_path(config_path: str | Path | None) -> None:
    global _active_config_path
    _active_config_path = config_path
    _load_config_from_path.cache_clear()


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {path}")
    return data


def _resolve_path(value: Any, base_dir: Path, default: Path) -> Path:
    if value is None:
        return default

    path = Path(str(value)).expanduser()
    if path.is_absolute():
        return path
    return base_dir / path


def _source_configs(value: Any, base_dir: Path) -> tuple[SourceConfig, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("Config key 'sources' must be a list.")

    sources = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            path = _resolve_path(item, base_dir, base_dir)
            sources.append(
                SourceConfig(
                    name=path.name or str(path),
                    path=path,
                    kinds=("model", "audio", "image"),
                )
            )
            continue

        if not isinstance(item, dict):
            raise ValueError(f"Config source #{index + 1} must be a string or mapping.")

        source_path = item.get("path")
        if not source_path:
            raise ValueError(f"Config source #{index + 1} is missing 'path'.")

        path = _resolve_path(source_path, base_dir, base_dir)
        kinds = item.get("kinds") or ["model", "audio", "image"]
        if not isinstance(kinds, list) or not all(isinstance(kind, str) for kind in kinds):
            raise ValueError(f"Config source #{index + 1} key 'kinds' must be a list of strings.")

        sources.append(
            SourceConfig(
                name=str(item.get("name") or path.name or path),
                path=path,
                kinds=tuple(kinds),
            )
        )

    return tuple(sources)


def _bool_value(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_base_url(value: Any) -> str:
    base_url = str(value or "/").strip()
    if not base_url or base_url == "/":
        return "/"
    if not base_url.startswith("/"):
        base_url = f"/{base_url}"
    return base_url.rstrip("/")


def load_config(config_path: str | Path | None = None) -> AppConfig:
    selected_path = config_path if config_path is not None else _active_config_path
    path = Path(selected_path) if selected_path is not None else default_config_path()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()
    return _load_config_from_path(path)


@lru_cache(maxsize=8)
def _load_config_from_path(path: Path) -> AppConfig:
    data = _read_yaml(path)
    server_data = data.get("server") or {}
    logging_data = data.get("logging") or {}
    auto_refresh_data = data.get("auto_refresh") or {}
    paths_data = data.get("paths") or {}
    if not isinstance(server_data, dict):
        raise ValueError("Config key 'server' must be a mapping.")
    if not isinstance(logging_data, dict):
        raise ValueError("Config key 'logging' must be a mapping.")
    if not isinstance(auto_refresh_data, dict):
        raise ValueError("Config key 'auto_refresh' must be a mapping.")
    if not isinstance(paths_data, dict):
        raise ValueError("Config key 'paths' must be a mapping.")

    base_dir = path.parent if path.is_file() else Path.cwd()
    data_dir = _resolve_path(paths_data.get("data_dir"), base_dir, Path.cwd() / ".warvault")
    database_path = _resolve_path(
        paths_data.get("database_path"),
        base_dir,
        data_dir / "warvault.sqlite3",
    )
    log_root_dir = _resolve_path(
        logging_data.get("root_dir"),
        base_dir,
        base_dir / "logs",
    )
    frontend_dist = repo_root() / "frontend" / "dist"

    return AppConfig(
        server=ServerConfig(
            host=str(server_data.get("host", "0.0.0.0")),
            port=int(server_data.get("port", 0)),
            base_url=_normalize_base_url(server_data.get("base_url", "/")),
        ),
        logging=LoggingConfig(
            enabled=_bool_value(logging_data.get("enabled"), True),
            level=str(logging_data.get("level", "INFO")).upper(),
            root_dir=log_root_dir,
        ),
        auto_refresh=AutoRefreshConfig(
            enabled=_bool_value(auto_refresh_data.get("enabled"), True),
            interval_seconds=max(5, int(auto_refresh_data.get("interval_seconds", 30))),
            initial_scan=_bool_value(auto_refresh_data.get("initial_scan"), True),
        ),
        paths=PathsConfig(
            data_dir=data_dir,
            database_path=database_path,
            frontend_dist=frontend_dist,
        ),
        sources=_source_configs(data.get("sources"), base_dir),
    )
