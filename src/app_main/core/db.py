from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app_main.core.paths import database_path


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    kinds TEXT NOT NULL DEFAULT 'model,audio,image',
    exclude TEXT NOT NULL DEFAULT '',
    last_scan_at TEXT,
    last_scan_summary TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    relative_path TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    format TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    metadata TEXT NOT NULL DEFAULT '{}',
    tags TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    favorite INTEGER NOT NULL DEFAULT 0,
    error TEXT NOT NULL DEFAULT '',
    scanned_at TEXT NOT NULL,
    UNIQUE(source_id, relative_path)
);

CREATE INDEX IF NOT EXISTS idx_assets_kind ON assets(kind);
CREATE INDEX IF NOT EXISTS idx_assets_format ON assets(format);
CREATE INDEX IF NOT EXISTS idx_assets_source ON assets(source_id);
CREATE INDEX IF NOT EXISTS idx_assets_name ON assets(name);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(database_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    init_db()
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
