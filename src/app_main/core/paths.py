from __future__ import annotations

from pathlib import Path

from app_main.config import load_config


def workspace_root() -> Path:
    return Path.cwd()


def data_dir() -> Path:
    path = load_config().paths.data_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    path = load_config().paths.database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
