from __future__ import annotations

from pathlib import Path

from app_main.config import load_config, set_config_path
from app_main.core.paths import database_path
from app_main.core.sources import list_sources


def test_config_can_seed_multiple_sources(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    config = tmp_path / "config.yaml"
    config.write_text(
        f"""
paths:
  data_dir: .warvault
  database_path: custom.sqlite3
server:
  base_url: vault
auto_refresh:
  enabled: true
  interval_seconds: 12
  initial_scan: true
sources:
  - {first.as_posix()}
  - name: Audio Only
    path: {second.as_posix()}
    kinds: [audio]
""",
        encoding="utf-8",
    )

    try:
        set_config_path(config)
        app_config = load_config()
        sources = list_sources()
    finally:
        set_config_path(None)

    assert len(sources) == 2
    by_path = {Path(source["path"]): source for source in sources}
    assert by_path[first.resolve()]["name"] == "first"
    assert by_path[second.resolve()]["name"] == "Audio Only"
    assert by_path[second.resolve()]["kinds"] == ["audio"]
    assert database_path() == tmp_path / "custom.sqlite3"
    assert app_config.server.base_url == "/vault"
    assert app_config.auto_refresh.enabled is True
    assert app_config.auto_refresh.interval_seconds == 12
    assert app_config.auto_refresh.initial_scan is True
