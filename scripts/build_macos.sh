#!/bin/bash
# 图片格式转换工具 — macOS 打包

set -e

cd "$(dirname "$0")/.."
APP_NAME="图片格式转换工具"

echo "=========================================="
echo "${APP_NAME} - macOS 打包"
echo "=========================================="

if ! command -v pyinstaller &>/dev/null && ! python3 -m PyInstaller --version &>/dev/null; then
  echo "错误: 请先安装 PyInstaller"
  echo "  pip install pyinstaller"
  exit 1
fi

PYINSTALLER_CMD="pyinstaller"
if ! command -v pyinstaller &>/dev/null; then
  PYINSTALLER_CMD="python3 -m PyInstaller"
fi

pip3 install -r requirements.txt

rm -rf build dist *.spec

ICON_PARAM=""
if [ -f "app_icon.icns" ]; then
  ICON_PARAM="--icon=app_icon.icns"
fi

$PYINSTALLER_CMD \
  --name="${APP_NAME}" \
  --windowed \
  --onedir \
  --clean \
  --noconfirm \
  --hidden-import=customtkinter \
  --hidden-import=PIL \
  --hidden-import=pillow_heif \
  --collect-all=pillow_heif \
  --add-data "shared:shared" \
  ${ICON_PARAM} \
  image_converter/gui_ctk.py

if [ -d "dist/${APP_NAME}.app" ] || [ -d "dist/${APP_NAME}" ]; then
  echo "✓ 打包成功"
  ls -la dist/
else
  echo "✗ 打包失败"
  exit 1
fi
