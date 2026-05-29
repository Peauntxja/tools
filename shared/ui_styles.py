"""UI 样式常量 — 对齐 git2logs / MIZUKI 工具箱深色风格。"""

from __future__ import annotations

import sys

try:
    import customtkinter as ctk
except ImportError:
    ctk = None  # type: ignore[assignment,misc]


def ui_font_family() -> str:
    if sys.platform == "darwin":
        return ".SF NS Text"
    if sys.platform == "win32":
        return "Segoe UI"
    return "DejaVu Sans"


def ctk_ui_font(size: int, weight: str = "normal"):
    if ctk is None:
        raise RuntimeError("需要安装 customtkinter: pip install customtkinter")
    family = ui_font_family()
    if weight in ("bold", "semibold"):
        return ctk.CTkFont(family=family, size=size, weight="bold")
    return ctk.CTkFont(family=family, size=size)


class UIStyles:
    """UI 样式统一管理。"""

    colors = {
        "bg_main": "#0A0A0F",
        "bg_card": "#0A0A0F",
        "bg_surface": "#1A1A23",
        "text_primary": "#FAFAFA",
        "text_secondary": "#8B8B9E",
        "text_tertiary": "#5A5A6E",
        "border": "#1A1A23",
        "accent": "#3ECFA5",
        "success": "#3ECFA5",
        "warning": "#EAB308",
        "error": "#DC2626",
        "hover": "#141419",
        "accent_hover": "#2BA882",
        "sidebar_bg": "#0A0A0F",
    }

    spacing = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 20, "xxl": 24}
    radius = {"sm": 6, "md": 7, "lg": 8, "xl": 10}

    fonts = {
        "header": lambda: ctk_ui_font(18, "bold"),
        "subheader": lambda: ctk_ui_font(14, "bold"),
        "body": lambda: ctk_ui_font(13),
        "caption": lambda: ctk_ui_font(11),
    }
