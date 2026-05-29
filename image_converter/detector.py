"""通过文件头检测真实图片格式（处理 HEIC 误标扩展名）。"""

from __future__ import annotations

from pathlib import Path

HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"heif", b"mif1", b"msf1"}


def detect_real_format(path: Path) -> str | None:
    """返回真实格式名（如 heic、png），无法识别时返回 None。"""
    try:
        with path.open("rb") as handle:
            header = handle.read(16)
    except OSError:
        return None

    if len(header) < 12:
        return None

    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if header[:3] == b"\xff\xd8\xff":
        return "jpg"
    if header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "webp"
    if header[:2] == b"BM":
        return "bmp"
    if header[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    if header[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"

    # ISO BMFF (HEIC/HEIF)
    if len(header) >= 12 and header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand in HEIF_BRANDS:
            return "heic"

    return None


def is_heic_file(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in {".heic", ".heif"}:
        return True
    return detect_real_format(path) == "heic"
