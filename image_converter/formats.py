"""图片格式与扩展名映射。"""

from __future__ import annotations

# 可作为输入的扩展名
INPUT_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".jpe",
    ".jfif",
    ".heic",
    ".heif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".gif",
}

# 可作为输出的格式
OUTPUT_FORMATS = ("png", "jpg", "jpeg", "webp")

FORMAT_TO_PIL: dict[str, str] = {
    "png": "PNG",
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "webp": "WEBP",
}

FORMAT_TO_EXT: dict[str, str] = {
    "png": ".png",
    "jpg": ".jpg",
    "jpeg": ".jpg",
    "webp": ".webp",
}

SIPS_FORMAT: dict[str, str] = {
    "png": "png",
    "jpg": "jpeg",
    "jpeg": "jpeg",
    "webp": "webp",
}


def normalize_format(fmt: str) -> str:
    value = fmt.lower().lstrip(".")
    if value == "jpeg":
        return "jpg"
    allowed = {"png", "jpg", "webp"}
    if value not in allowed:
        raise ValueError(f"不支持的目标格式: {fmt}，可选: {', '.join(sorted(allowed))}")
    return value


def target_extension(fmt: str) -> str:
    normalized = normalize_format(fmt)
    return FORMAT_TO_EXT.get(normalized, f".{normalized}")
