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
