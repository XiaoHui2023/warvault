from __future__ import annotations

from pathlib import Path

from app_main.core.assets import get_asset, list_assets, update_asset
from app_main.core.sources import add_source, list_sources, scan_source


def test_scan_source_and_update_metadata(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_root = tmp_path / "source"
    source_root.mkdir()
    image = source_root / "icons" / "hero.png"
    image.parent.mkdir()
    image.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x10\x00\x00\x00\x20"
        b"\x08\x06\x00\x00\x00"
    )
    audio = source_root / "sound.wav"
    audio.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt ")

    source = add_source("素材", str(source_root))
    summary = scan_source(source["id"])
    assets = list_assets()

    assert summary["added"] == 2
    assert len(list_sources()) == 1
    assert {asset["kind"] for asset in assets} == {"image", "audio"}

    asset = next(item for item in assets if item["kind"] == "image")
    assert asset["metadata"]["width"] == 16
    assert asset["metadata"]["height"] == 32

    updated = update_asset(asset["id"], tags=["unit/hero", "race/undead"], description="亡灵英雄图标", favorite=True)
    assert updated is not None
    assert updated["favorite"] is True
    assert updated["tags"] == ["race/undead", "unit/hero"]

    image.unlink()
    missing = scan_source(source["id"])
    stored = get_asset(asset["id"])

    assert missing["missing"] == 1
    assert stored is not None
    assert stored["status"] == "missing"
    assert stored["description"] == "亡灵英雄图标"
