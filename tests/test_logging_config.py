from __future__ import annotations

import logging
from pathlib import Path

from app_main.config import load_config, set_config_path
from app_main.logging_setup import setup_logging


def test_logging_root_dir_creates_split_session_logs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "config.yaml"
    config.write_text(
        """
logging:
  enabled: true
  level: INFO
  root_dir: logs
""",
        encoding="utf-8",
    )

    try:
        set_config_path(config)
        app_config = load_config()
        session_dir = setup_logging(app_config.logging)
        logger = logging.getLogger("warvault.test")
        logger.info("run log smoke")
        logger.debug("debug log smoke")
        logger.error("error log smoke")
    finally:
        set_config_path(None)

    assert session_dir is not None
    assert session_dir.parent.parent == tmp_path / "logs"
    assert (session_dir / "run.log").is_file()
    assert (session_dir / "error.log").is_file()
    assert (session_dir / "modules" / "warvault.test.log").is_file()
    assert "run log smoke" in (session_dir / "run.log").read_text(encoding="utf-8")
    assert "error log smoke" in (session_dir / "error.log").read_text(encoding="utf-8")
    assert "debug log smoke" in (session_dir / "modules" / "warvault.test.log").read_text(encoding="utf-8")


def test_default_logging_root_is_logs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "config.yaml"
    config.write_text("logging:\n  enabled: true\n", encoding="utf-8")

    try:
        set_config_path(config)
        app_config = load_config()
    finally:
        set_config_path(None)

    assert app_config.logging.root_dir == Path(tmp_path / "logs")
