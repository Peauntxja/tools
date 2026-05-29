#!/usr/bin/env python3
"""图片格式转换 — 命令行入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from image_converter.converter import ConvertOptions, convert_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="批量转换文件夹中的图片格式（支持 PNG/JPG/WebP/HEIC 等）",
    )
    parser.add_argument("input_dir", type=Path, help="要处理的文件夹")
    parser.add_argument(
        "-t",
        "--to",
        required=True,
        help="目标格式: png, jpg, webp",
    )
    parser.add_argument(
        "--from",
        dest="source_format",
        default=None,
        help="仅转换指定源格式",
    )
    parser.add_argument("-o", "--output-dir", type=Path, default=None)
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("--delete-original", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--quality", type=int, default=95)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    options = ConvertOptions(
        input_dir=args.input_dir,
        target_format=args.to,
        output_dir=args.output_dir,
        recursive=args.recursive,
        delete_original=args.delete_original,
        skip_existing=args.skip_existing,
        quality=args.quality,
        source_format=args.source_format,
    )

    def on_log(message: str, level: str) -> None:
        stream = sys.stderr if level == "error" else sys.stdout
        print(message, file=stream)

    try:
        result = convert_directory(options, on_log=on_log)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
