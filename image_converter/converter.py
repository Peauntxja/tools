"""图片格式转换核心逻辑。"""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps

from image_converter.detector import detect_real_format, is_heic_file
from image_converter.formats import (
    FORMAT_TO_PIL,
    INPUT_EXTENSIONS,
    normalize_format,
    target_extension,
)

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIC_SUPPORTED = True
except ImportError:
    HEIC_SUPPORTED = False

LogCallback = Callable[[str, str], None]


@dataclass
class ConvertOptions:
    input_dir: Path
    target_format: str
    output_dir: Path | None = None
    recursive: bool = False
    delete_original: bool = False
    skip_existing: bool = False
    quality: int = 95
    source_format: str | None = None


@dataclass
class ConvertResult:
    converted: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)


def iter_image_files(root: Path, recursive: bool) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    files: list[Path] = []
    for path in root.glob(pattern):
        if not path.is_file():
            continue
        if path.suffix.lower() not in INPUT_EXTENSIONS:
            continue
        files.append(path)
    return sorted(files)


def resolve_output_path(
    source: Path,
    input_root: Path,
    output_root: Path | None,
    target_fmt: str,
) -> Path:
    ext = target_extension(target_fmt)
    if output_root is None:
        return source.with_suffix(ext)
    relative = source.relative_to(input_root)
    return (output_root / relative).with_suffix(ext)


def open_image(source: Path) -> Image.Image:
    with Image.open(source) as img:
        return ImageOps.exif_transpose(img).copy()


def prepare_for_jpeg(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        return background
    if image.mode == "P" and "transparency" in image.info:
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def prepare_for_png(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA"):
        return image
    if image.mode == "P":
        if "transparency" in image.info:
            return image.convert("RGBA")
        return image.convert("RGB")
    if image.mode == "CMYK":
        return image.convert("RGB")
    if image.mode in ("L", "1"):
        return image.convert("RGB")
    return image.convert("RGB")


def convert_with_sips(source: Path, target: Path, target_fmt: str) -> None:
    from image_converter.formats import SIPS_FORMAT

    if platform.system() != "Darwin" or shutil.which("sips") is None:
        raise RuntimeError("未安装 pillow-heif，且当前环境不支持 macOS sips。")

    sips_fmt = SIPS_FORMAT.get(normalize_format(target_fmt))
    if not sips_fmt:
        raise RuntimeError(f"sips 不支持输出格式: {target_fmt}")

    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["sips", "-s", "format", sips_fmt, str(source), "--out", str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"sips 转换失败: {stderr}")


def save_image(image: Image.Image, target: Path, target_fmt: str, quality: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fmt = normalize_format(target_fmt)
    pil_format = FORMAT_TO_PIL[fmt]

    if fmt in ("jpg", "jpeg"):
        prepare_for_jpeg(image).save(
            target,
            format=pil_format,
            quality=quality,
            optimize=True,
        )
    elif fmt == "png":
        prepare_for_png(image).save(
            target,
            format=pil_format,
            optimize=True,
            compress_level=max(0, min(9, 10 - quality // 12)),
        )
    elif fmt == "webp":
        image.save(target, format=pil_format, quality=quality)
    else:
        image.save(target, format=pil_format)


def convert_file(
    source: Path,
    target: Path,
    target_fmt: str,
    *,
    delete_original: bool,
    skip_existing: bool,
    quality: int,
) -> str:
    if skip_existing and target.exists():
        return "skipped"

    if source.resolve() == target.resolve():
        return "skipped"

    use_sips = is_heic_file(source) and not HEIC_SUPPORTED

    if use_sips:
        convert_with_sips(source, target, target_fmt)
    else:
        image = open_image(source)
        save_image(image, target, target_fmt, quality)

    if delete_original and source.exists():
        source.unlink()

    return "converted"


def convert_directory(
    options: ConvertOptions,
    on_log: LogCallback | None = None,
) -> ConvertResult:
    def log(message: str, level: str = "info") -> None:
        if on_log:
            on_log(message, level)

    result = ConvertResult()
    input_dir = options.input_dir.expanduser().resolve()
    target_fmt = normalize_format(options.target_format)

    if not input_dir.is_dir():
        raise FileNotFoundError(f"目录不存在: {input_dir}")

    output_dir = (
        options.output_dir.expanduser().resolve()
        if options.output_dir
        else None
    )
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)

    source_filter = (
        normalize_format(options.source_format)
        if options.source_format
        else None
    )

    files = iter_image_files(input_dir, options.recursive)
    if source_filter:

        def _matches_source(path: Path) -> bool:
            real = detect_real_format(path)
            suffix = path.suffix.lower().lstrip(".")
            effective = "jpg" if (real or suffix) in ("jpeg", "jpe", "jfif") else (real or suffix)
            if effective == "jpeg":
                effective = "jpg"
            return effective == source_filter

        files = [f for f in files if _matches_source(f)]

    if not files:
        log(f"未在 {input_dir} 中找到可转换的图片。", "warning")
        return result

    log(f"共找到 {len(files)} 个文件，目标格式: {target_fmt.upper()}", "info")

    for source in files:
        target = resolve_output_path(source, input_dir, output_dir, target_fmt)
        try:
            status = convert_file(
                source,
                target,
                target_fmt,
                delete_original=options.delete_original,
                skip_existing=options.skip_existing,
                quality=options.quality,
            )
            if status == "converted":
                result.converted += 1
                log(f"[OK] {source.name} -> {target.name}", "success")
            else:
                result.skipped += 1
                log(f"[SKIP] {source.name}", "warning")
        except Exception as exc:
            result.failed += 1
            msg = f"[FAIL] {source.name}: {exc}"
            result.errors.append(msg)
            log(msg, "error")

    log(
        f"完成: 转换 {result.converted}，跳过 {result.skipped}，失败 {result.failed}",
        "success" if result.failed == 0 else "warning",
    )
    return result
