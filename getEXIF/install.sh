#!/bin/bash
# EXIF 工具依赖安装脚本

echo "正在安装 EXIF 工具依赖..."
echo "Python 版本:"
python3 --version

echo ""
echo "正在安装依赖包..."
python3 -m pip install --user -r requirements.txt

echo ""
echo "验证安装..."
python3 -c "from PIL import Image, ExifTags; import piexif; print('✓ 所有依赖已成功安装')"

echo ""
echo "安装完成！"

