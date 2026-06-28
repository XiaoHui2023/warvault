from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "src"), "--version"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0
    assert "warvault 0.0.0" in result.stdout


def test_module_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app_main", "--version"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0
    assert "warvault 0.0.0" in result.stdout


def test_help() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "src"), "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0
    assert "warvault" in result.stdout


def test_status_api(tmp_path) -> None:
    from fastapi.testclient import TestClient

    from app_main.app import create_app

    config = tmp_path / "config.yaml"
    config.write_text("auto_refresh:\n  enabled: false\n", encoding="utf-8")
    client = TestClient(create_app(config_path=str(config)))
    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json()["name"] == "warvault"


def test_base_url_mounts_api(tmp_path) -> None:
    from fastapi.testclient import TestClient

    from app_main.app import create_app

    config = tmp_path / "config.yaml"
    config.write_text(
        """
server:
  base_url: /vault/
auto_refresh:
  enabled: false
""",
        encoding="utf-8",
    )
    client = TestClient(create_app(config_path=str(config)))

    response = client.get("/vault/api/status")

    assert response.status_code == 200
    assert response.json()["name"] == "warvault"
