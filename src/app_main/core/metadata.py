from __future__ import annotations

import struct
import wave
from pathlib import Path


def read_metadata(path: Path, kind: str) -> tuple[dict, str]:
    try:
        if kind == "image":
            return _image_metadata(path), ""
        if kind == "audio":
            return _audio_metadata(path), ""
        if kind == "model":
            return _model_metadata(path), ""
    except Exception as exc:
        return {}, str(exc)
    return {}, ""


def _image_metadata(path: Path) -> dict:
    suffix = path.suffix.lower()
    if suffix == ".png":
        with path.open("rb") as file:
            header = file.read(24)
        if header[:8] == b"\x89PNG\r\n\x1a\n":
            width, height = struct.unpack(">II", header[16:24])
            return {"width": width, "height": height}
    if suffix in {".jpg", ".jpeg"}:
        return _jpeg_size(path)
    if suffix == ".webp":
        return _webp_size(path)
    if suffix == ".tga":
        with path.open("rb") as file:
            header = file.read(18)
        if len(header) == 18:
            width, height = struct.unpack("<HH", header[12:16])
            return {"width": width, "height": height}
    if suffix == ".dds":
        with path.open("rb") as file:
            header = file.read(20)
        if header[:4] == b"DDS ":
            height, width = struct.unpack("<II", header[12:20])
            return {"width": width, "height": height}
    return {}


def _jpeg_size(path: Path) -> dict:
    with path.open("rb") as file:
        data = file.read()
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            height, width = struct.unpack(">HH", data[index + 3 : index + 7])
            return {"width": width, "height": height}
        length = struct.unpack(">H", data[index : index + 2])[0]
        index += length
    return {}


def _webp_size(path: Path) -> dict:
    with path.open("rb") as file:
        data = file.read(30)
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return {}
    if data[12:16] == b"VP8X" and len(data) >= 30:
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return {"width": width, "height": height}
    return {}


def _audio_metadata(path: Path) -> dict:
    if path.suffix.lower() != ".wav":
        return {}
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        return {
            "duration": round(frames / float(rate), 3) if rate else 0,
            "sample_rate": rate,
            "channels": wav.getnchannels(),
        }


def _model_metadata(path: Path) -> dict:
    return {"preview_status": "not_converted", "bytes": path.stat().st_size}
