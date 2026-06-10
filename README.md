# MIZUKI Tools

个人小工具集合仓库，每个子目录为一个独立工具。

远程仓库：[https://github.com/Peauntxja/tools](https://github.com/Peauntxja/tools)

## 工具列表

| 工具 | 说明 | 入口 |
|------|------|------|
| image_converter | 批量图片格式转换（PNG / JPG / WebP / HEIC） | `image_converter/gui_ctk.py` |
| reptile-rsj-sh-gov-cn | 上海市人社局社保稽核 / 仲裁公告爬虫 | `reptile-rsj-sh-gov-cn/main.py` |
| reptile-12306-station | 12306 车站数据处理（CSV / JSON） | `reptile-12306-station/station_data_processor.py` |
| getEXIF | 读取与修改图片 EXIF 信息 | `getEXIF/exif_tool.py` |
| concurrent-test | API 并发、幂等性与安全性测试框架 | `concurrent-test/main.py` |
| wenshu-export | 裁判文书网文书导出（带水印 HTML / PDF） | `wenshu-export/wenshu-export` |
| dashscope_stress | DashScope Anthropic 兼容 API 压力测试 | `dashscope_stress/stress_test.py` |

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
