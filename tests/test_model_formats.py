from __future__ import annotations

from app_main.core.assets import list_assets, resolve_asset_related_file
from app_main.core.sources import add_source, scan_source


def test_model_source_accepts_unknown_model_formats(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_root = tmp_path / "models"
    source_root.mkdir()
    custom_model = source_root / "hero.y3model"
    custom_model.write_text("model payload", encoding="utf-8")

    source = add_source("Models", str(source_root), kinds=["model"])
    summary = scan_source(source["id"])
    assets = list_assets(kind="model")

    assert summary["added"] == 1
    assert len(assets) == 1
    assert assets[0]["name"] == "hero"
    assert assets[0]["kind"] == "model"
    assert assets[0]["format"] == "y3model"


def test_model_directory_is_one_asset_package(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_root = tmp_path / "models"
    source_root.mkdir()
    (source_root / "hero.fbx").write_bytes(b"fbx")
    (source_root / "hero.mdx").write_bytes(b"mdx")
    (source_root / "hero.json").write_text("{}", encoding="utf-8")
    (source_root / "hero.tga").write_bytes(b"tga")

    source = add_source("Models", str(source_root), kinds=["model"])
    summary = scan_source(source["id"])
    assets = list_assets(kind="model")

    assert summary["added"] == 1
    assert len(assets) == 1
    assert assets[0]["name"] == "hero"
    assert assets[0]["format"] == "fbx"
    assert assets[0]["relative_path"] == "hero.fbx"
    assert assets[0]["metadata"]["package_files"] == 4


def test_model_related_file_resolves_inside_source_root(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_root = tmp_path / "models"
    package_root = source_root / "hero"
    package_root.mkdir(parents=True)
    (package_root / "hero.mdx").write_bytes(b"mdx")
    (package_root / "hero.blp").write_bytes(b"blp")
    (source_root / "outside.blp").write_bytes(b"outside")

    source = add_source("Models", str(source_root), kinds=["model"])
    scan_source(source["id"])
    asset = list_assets(kind="model")[0]

    assert resolve_asset_related_file(asset["id"], "hero.blp") == package_root / "hero.blp"
    assert resolve_asset_related_file(asset["id"], "../outside.blp") == source_root / "outside.blp"
    assert resolve_asset_related_file(asset["id"], "../../escape.blp") is None


def test_y3_package_prefers_meta_source_path_and_texture_mapping(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_root = tmp_path / "models"
    package_root = source_root / "Peasant.package"
    texture_root = package_root / "textures"
    texture_root.mkdir(parents=True)
    (package_root / "Peasant.mdl").write_bytes(b"mdl")
    (package_root / "Peasant.mdx").write_bytes(b"mdx")
    (texture_root / "Peasant.tga").write_bytes(b"tga")
    (package_root / "meta.json").write_text(
        '{"source_path":"Peasant.mdx","textures":{"Textures/Peasant":"Peasant.tga"}}',
        encoding="utf-8",
    )

    source = add_source("Models", str(source_root), kinds=["model"])
    scan_source(source["id"])
    asset = list_assets(kind="model")[0]

    assert asset["name"] == "Peasant"
    assert asset["format"] == "mdx"
    assert asset["relative_path"] == "Peasant.package/Peasant.mdx"
    assert asset["metadata"]["package_files"] == 4
    assert resolve_asset_related_file(asset["id"], "Textures/Peasant.blp") == texture_root / "Peasant.tga"


def test_related_file_falls_back_to_textures_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_root = tmp_path / "models"
    package_root = source_root / "rogue.package"
    texture_root = package_root / "textures"
    texture_root.mkdir(parents=True)
    (package_root / "model.fbx").write_bytes(b"fbx")
    (texture_root / "rogue_texture.png").write_bytes(b"png")

    source = add_source("Models", str(source_root), kinds=["model"])
    scan_source(source["id"])
    asset = list_assets(kind="model")[0]

    assert resolve_asset_related_file(asset["id"], "rogue_texture.png") == texture_root / "rogue_texture.png"


def test_related_file_falls_back_to_fbx_fbm_directory(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_root = tmp_path / "models"
    package_root = source_root / "rogue.package"
    texture_root = package_root / "model.fbm"
    texture_root.mkdir(parents=True)
    (package_root / "model.fbx").write_bytes(b"fbx")
    (texture_root / "rogue_texture.png").write_bytes(b"png")

    source = add_source("Models", str(source_root), kinds=["model"])
    scan_source(source["id"])
    asset = list_assets(kind="model")[0]

    assert resolve_asset_related_file(asset["id"], "rogue_texture.png") == texture_root / "rogue_texture.png"
