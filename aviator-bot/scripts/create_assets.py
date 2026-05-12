"""Gera assets PNG locais sem versionar binários no Git.

Uso:
  python scripts/create_assets.py
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "assets"


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def write_solid_png(path: Path, rgb: tuple[int, int, int], width: int = 96, height: int = 96) -> None:
    raw_rows = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw_rows, 9))
        + _chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def main() -> int:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    assets = {
        "green.png": (57, 255, 136),
        "signal.png": (255, 159, 28),
    }
    for filename, color in assets.items():
        path = ASSETS_DIR / filename
        if not path.exists():
            write_solid_png(path, color)
            print(f"✅ Asset criado: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
