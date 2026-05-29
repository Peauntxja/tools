# MIZUKI Tools

个人小工具集合仓库，每个子目录为一个独立工具。

远程仓库：[https://github.com/Peauntxja/tools](https://github.com/Peauntxja/tools)

## 工具列表

| 工具 | 说明 | 入口 |
|------|------|------|
| image_converter | 批量图片格式转换（PNG / JPG / WebP / HEIC） | `image_converter/gui_ctk.py` |

## 图片格式转换工具

### 功能

- 自由选择目标格式：PNG、JPG、WebP
- 支持输入：HEIC、HEIF、PNG、JPG、JPEG、WebP、BMP、TIFF、GIF
- 自动校正 EXIF 旋转方向
- 识别 HEIC 误标扩展名（如 `.png` 实为 HEIC）
- macOS 下 HEIC 可通过 `sips` 回退转换
- 递归子目录、删除原文件、跳过已存在

### 安装依赖

```bash
cd /Users/kusuri_mizuki/myProject/tools
pip install -r requirements.txt
```

### 图形界面（推荐）

```bash
python image_converter/gui_ctk.py
```

### 命令行

```bash
python -m image_converter.cli /path/to/images --to jpg -r --delete-original
```

### 打包

详见 [PACKAGING.md](PACKAGING.md)。

- macOS: `./scripts/build_macos.sh`
- Windows: `scripts\build_windows.bat`

预编译包见 GitHub Releases（推送 `v*` 标签后自动构建）。

## 开发

UI 风格对齐 [git2logs](https://github.com/Peauntxja/git2logs)（CustomTkinter 深色主题）。

共享样式模块：`shared/ui_styles.py`
