#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图片格式转换工具 — CustomTkinter 图形界面。"""

from __future__ import annotations

import queue
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

try:
    import customtkinter as ctk
except ImportError:
    print("错误: 需要安装 customtkinter。请运行: pip install customtkinter")
    sys.exit(1)

# 支持直接运行与 PyInstaller 打包
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from image_converter.converter import ConvertOptions, convert_directory
from shared.ui_styles import UIStyles, ctk_ui_font, ui_font_family


def _resolve_monospace_font(root, size: int = 11) -> tuple[str, int]:
    try:
        from tkinter import font as tkfont

        families = set(tkfont.families(root))
    except Exception:
        families = set()
    for name in ("JetBrains Mono", "Menlo", "Monaco", "Consolas", "Courier New"):
        if name in families:
            return (name, size)
    return ("Courier", size)


class ImageConverterGUI:
  def __init__(self, root: ctk.CTk) -> None:
    self.root = root
    self.root.title("图片格式转换工具")
    self.root.minsize(720, 560)
    self.root.geometry("860x640")

    self.styles = UIStyles
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    self._log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
    self._log_pending: list[tuple[str, str]] = []
    self._log_flush_scheduled = False
    self._is_running = False

    self.folder_path = ctk.StringVar(value="")
    self.target_format = ctk.StringVar(value="jpg")
    self.recursive = ctk.BooleanVar(value=True)
    self.delete_original = ctk.BooleanVar(value=False)
    self.skip_existing = ctk.BooleanVar(value=False)
    self.quality = ctk.IntVar(value=95)

    self._build_ui()
    self.root.after(80, self._poll_log_queue)

  def _build_ui(self) -> None:
    c = self.styles.colors
    self.root.configure(fg_color=c["bg_main"])

    main = ctk.CTkFrame(self.root, fg_color=c["bg_main"], corner_radius=0)
    main.pack(fill="both", expand=True)

    topbar = ctk.CTkFrame(main, fg_color=c["bg_card"], height=72, corner_radius=0)
    topbar.pack(fill="x")
    topbar.pack_propagate(False)
    topbar_inner = ctk.CTkFrame(topbar, fg_color="transparent")
    topbar_inner.pack(fill="both", expand=True, padx=20, pady=16)
    ctk.CTkLabel(
      topbar_inner,
      text="图片格式转换",
      font=ctk_ui_font(18, "bold"),
      text_color=c["text_primary"],
      anchor="w",
    ).pack(anchor="w")
    ctk.CTkLabel(
      topbar_inner,
      text="批量将文件夹内图片转换为目标格式（支持 HEIC / PNG / JPG / WebP）",
      font=ctk_ui_font(12),
      text_color=c["text_secondary"],
      anchor="w",
    ).pack(anchor="w")

    ctk.CTkFrame(main, fg_color=c["border"], height=1, corner_radius=0).pack(fill="x")

    body = ctk.CTkScrollableFrame(main, fg_color=c["bg_main"], corner_radius=0)
    body.pack(fill="both", expand=True, padx=20, pady=16)

    card = ctk.CTkFrame(body, fg_color=c["bg_surface"], corner_radius=self.styles.radius["lg"])
    card.pack(fill="x", pady=(0, 12))

    inner = ctk.CTkFrame(card, fg_color="transparent")
    inner.pack(fill="x", padx=16, pady=16)

    ctk.CTkLabel(
      inner, text="文件夹", font=ctk_ui_font(13, "bold"),
      text_color=c["text_primary"], anchor="w",
    ).pack(anchor="w", pady=(0, 6))

    folder_row = ctk.CTkFrame(inner, fg_color="transparent")
    folder_row.pack(fill="x", pady=(0, 12))
    self.folder_entry = ctk.CTkEntry(
      folder_row, textvariable=self.folder_path, height=36,
      font=ctk_ui_font(13), fg_color=c["bg_main"], border_color=c["border"],
    )
    self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
    ctk.CTkButton(
      folder_row, text="浏览", width=80, height=36,
      fg_color=c["bg_main"], hover_color=c["hover"],
      border_color=c["border"], border_width=1,
      command=self._browse_folder,
    ).pack(side="right")

    ctk.CTkLabel(
      inner, text="目标格式", font=ctk_ui_font(13, "bold"),
      text_color=c["text_primary"], anchor="w",
    ).pack(anchor="w", pady=(0, 6))

    format_row = ctk.CTkFrame(inner, fg_color="transparent")
    format_row.pack(fill="x", pady=(0, 12))
    for fmt, label in (("png", "PNG"), ("jpg", "JPG"), ("webp", "WebP")):
      ctk.CTkRadioButton(
        format_row, text=label, variable=self.target_format, value=fmt,
        font=ctk_ui_font(13), fg_color=c["accent"], hover_color=c["accent_hover"],
      ).pack(side="left", padx=(0, 20))

    opts = ctk.CTkFrame(inner, fg_color="transparent")
    opts.pack(fill="x", pady=(0, 8))
    ctk.CTkCheckBox(
      opts, text="递归子文件夹", variable=self.recursive,
      font=ctk_ui_font(13), fg_color=c["accent"], hover_color=c["accent_hover"],
    ).pack(anchor="w", pady=2)
    ctk.CTkCheckBox(
      opts, text="转换后删除原文件", variable=self.delete_original,
      font=ctk_ui_font(13), fg_color=c["accent"], hover_color=c["accent_hover"],
    ).pack(anchor="w", pady=2)
    ctk.CTkCheckBox(
      opts, text="目标已存在则跳过", variable=self.skip_existing,
      font=ctk_ui_font(13), fg_color=c["accent"], hover_color=c["accent_hover"],
    ).pack(anchor="w", pady=2)

    quality_row = ctk.CTkFrame(inner, fg_color="transparent")
    quality_row.pack(fill="x", pady=(8, 0))
    ctk.CTkLabel(
      quality_row, text="JPG/WebP 质量", font=ctk_ui_font(13),
      text_color=c["text_secondary"],
    ).pack(side="left")
    self.quality_label = ctk.CTkLabel(
      quality_row, text="95", font=ctk_ui_font(13), text_color=c["accent"], width=30,
    )
    self.quality_label.pack(side="right")
    ctk.CTkSlider(
      inner, from_=60, to=100, number_of_steps=40,
      variable=self.quality, command=self._on_quality_change,
      progress_color=c["accent"], button_color=c["accent"],
      button_hover_color=c["accent_hover"],
    ).pack(fill="x", pady=(4, 0))

    log_card = ctk.CTkFrame(body, fg_color=c["bg_surface"], corner_radius=self.styles.radius["lg"])
    log_card.pack(fill="both", expand=True)
    log_header = ctk.CTkFrame(log_card, fg_color="transparent")
    log_header.pack(fill="x", padx=16, pady=(12, 6))
    ctk.CTkLabel(
      log_header, text="执行日志", font=ctk_ui_font(13, "bold"),
      text_color=c["text_primary"],
    ).pack(side="left")
    ctk.CTkButton(
      log_header, text="清空", width=60, height=28,
      fg_color=c["bg_main"], hover_color=c["hover"],
      border_color=c["border"], border_width=1,
      command=self._clear_logs,
    ).pack(side="right")

    mono = _resolve_monospace_font(self.root)
    self.log_text = ctk.CTkTextbox(
      log_card, font=ctk.CTkFont(family=mono[0], size=mono[1]),
      fg_color=c["bg_main"], text_color=c["text_primary"],
      border_color=c["border"], border_width=1, corner_radius=self.styles.radius["md"],
    )
    self.log_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))
    self._setup_log_tags()

    bottom = ctk.CTkFrame(main, fg_color=c["bg_main"], corner_radius=0)
    bottom.pack(fill="x", padx=20, pady=(0, 16))
    self.convert_btn = ctk.CTkButton(
      bottom, text="开始转换", height=44,
      font=ctk_ui_font(15, "bold"),
      fg_color=c["accent"], hover_color=c["accent_hover"],
      text_color="#0A0A0F",
      command=self._start_convert,
    )
    self.convert_btn.pack(fill="x")

    self.log("就绪。请选择文件夹与目标格式后点击「开始转换」。", "info")

  def _setup_log_tags(self) -> None:
    c = self.styles.colors
  # CTkTextbox uses underlying tk Text — configure tags on _textbox
    text = self.log_text._textbox  # noqa: SLF001
    text.tag_configure("success", foreground=c["success"])
    text.tag_configure("error", foreground=c["error"])
    text.tag_configure("warning", foreground=c["warning"])
    text.tag_configure("info", foreground=c["text_secondary"])

  def _on_quality_change(self, value: float) -> None:
    self.quality_label.configure(text=str(int(value)))

  def _browse_folder(self) -> None:
    directory = filedialog.askdirectory(title="选择图片文件夹")
    if directory:
      self.folder_path.set(directory)

  def log(self, message: str, log_type: str = "info") -> None:
    if threading.current_thread() is not threading.main_thread():
      self._log_queue.put((message, log_type))
      return
    self._log_pending.append((message, log_type))
    if not self._log_flush_scheduled:
      self._log_flush_scheduled = True
      self.root.after(100, self._flush_logs)

  def _poll_log_queue(self) -> None:
    try:
      while True:
        self._log_pending.append(self._log_queue.get_nowait())
    except queue.Empty:
      pass
    if self._log_pending and not self._log_flush_scheduled:
      self._log_flush_scheduled = True
      self.root.after(100, self._flush_logs)
    self.root.after(80, self._poll_log_queue)

  def _flush_logs(self) -> None:
    self._log_flush_scheduled = False
    if not self._log_pending:
      return
    pending = self._log_pending[:]
    self._log_pending.clear()
    text = self.log_text._textbox  # noqa: SLF001
    for message, log_type in pending:
      ts = datetime.now().strftime("%H:%M:%S")
      prefix = {"success": "[OK]", "error": "[FAIL]", "warning": "[SKIP]", "info": "[INFO]"}.get(
        log_type, "[INFO]"
      )
      line = f"{ts} {prefix} {message}\n"
      start = text.index("end-1c")
      text.insert("end", line)
      tag_start = f"{start} linestart + {len(ts) + 1} chars"
      tag_end = f"{start} linestart + {len(ts) + 1 + len(prefix)} chars"
      text.tag_add(log_type, tag_start, tag_end)
    text.see("end")

  def _clear_logs(self) -> None:
    self.log_text.delete("1.0", "end")
    while not self._log_queue.empty():
      try:
        self._log_queue.get_nowait()
      except queue.Empty:
        break
    self._log_pending.clear()

  def _set_running(self, running: bool) -> None:
    self._is_running = running
    state = "disabled" if running else "normal"
    self.convert_btn.configure(state=state, text="转换中..." if running else "开始转换")

  def _start_convert(self) -> None:
    if self._is_running:
      return
    folder = self.folder_path.get().strip()
    if not folder:
      messagebox.showwarning("提示", "请先选择文件夹。")
      return
    path = Path(folder)
    if not path.is_dir():
      messagebox.showerror("错误", f"目录不存在:\n{folder}")
      return

    options = ConvertOptions(
      input_dir=path,
      target_format=self.target_format.get(),
      recursive=self.recursive.get(),
      delete_original=self.delete_original.get(),
      skip_existing=self.skip_existing.get(),
      quality=int(self.quality.get()),
    )

    self._set_running(True)
    self.log(f"开始转换 -> {options.target_format.upper()}", "info")

    def worker() -> None:
      try:
        result = convert_directory(options, on_log=self.log)
        summary = (
          f"转换完成\n\n"
          f"成功: {result.converted}\n"
          f"跳过: {result.skipped}\n"
          f"失败: {result.failed}"
        )
        self.root.after(
          0,
          lambda: messagebox.showinfo(
            "完成" if result.failed == 0 else "完成（有失败）",
            summary,
          ),
        )
      except Exception as exc:
        self.log(str(exc), "error")
        self.root.after(0, lambda: messagebox.showerror("错误", str(exc)))
      finally:
        self.root.after(0, lambda: self._set_running(False))

    threading.Thread(target=worker, daemon=True).start()


def main() -> None:
  root = ctk.CTk()
  app = ImageConverterGUI(root)
  root.mainloop()


if __name__ == "__main__":
  main()
