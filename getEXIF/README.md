# EXIF 信息工具

一个用于读取和修改图片 EXIF 信息的 Python 工具。

## 功能特性

- ✅ 读取图片的 EXIF 元数据信息
- ✅ 修改图片的 EXIF 信息（支持常用字段）
- ✅ 批量处理目录中的图片
- ✅ 支持文本和 JSON 两种输出格式
- ✅ 修改前自动备份原图
- ✅ 支持 JPEG、TIFF 和 PNG 格式

## 安装

1. 确保已安装 Python 3.6 或更高版本

2. 安装依赖：
```bash
pip install -r requirements.txt
```

或者使用用户安装模式（推荐）：
```bash
python3 -m pip install --user -r requirements.txt
```

### 故障排除

如果遇到 `ModuleNotFoundError: No module named 'PIL'` 错误：

1. **确认 Python 解释器**：确保你使用的 Python 解释器与安装依赖时使用的相同
   ```bash
   # 检查 Python 路径
   which python3
   python3 --version
   ```

2. **重新安装依赖**：
   ```bash
   python3 -m pip install --user --upgrade -r requirements.txt
   ```

3. **验证安装**：
   ```bash
   python3 -c "from PIL import Image, ExifTags; import piexif; print('依赖安装成功')"
   ```

4. **如果使用 IDE**：确保 IDE 使用的 Python 解释器与命令行中的相同。可以在 IDE 设置中配置 Python 解释器路径。

## 使用方法

### 读取 EXIF 信息

读取单个图片的 EXIF 信息：
```bash
python exif_tool.py --read image.jpg
```

以 JSON 格式输出：
```bash
python exif_tool.py --read image.jpg --output json
```

### 修改 EXIF 信息

修改拍摄日期：
```bash
python exif_tool.py --modify image.jpg --field DateTimeOriginal --value "2025:01:01 12:00:00"
```

修改其他字段（例如相机型号）：
```bash
python exif_tool.py --modify image.jpg --ifd 0th --field Model --value "My Camera"
```

修改时不创建备份：
```bash
python exif_tool.py --modify image.jpg --field DateTimeOriginal --value "2025:01:01 12:00:00" --no-backup
```

### 批量处理

批量读取目录中所有图片的 EXIF 信息：
```bash
python exif_tool.py --batch ./images
```

批量修改目录中所有图片的 EXIF 信息：
```bash
python exif_tool.py --batch ./images --modify --field DateTimeOriginal --value "2025:01:01 12:00:00"
```

## 常用 EXIF 字段

### 0th IFD（主图像信息）
- `Make`: 相机制造商
- `Model`: 相机型号
- `DateTime`: 文件修改日期时间
- `Orientation`: 图像方向

### Exif IFD（EXIF 子信息）
- `DateTimeOriginal`: 拍摄日期时间
- `DateTimeDigitized`: 数字化日期时间
- `ExposureTime`: 曝光时间
- `FNumber`: 光圈值
- `ISOSpeedRatings`: ISO 感光度
- `FocalLength`: 焦距

### GPS IFD（GPS 信息）
- `GPSLatitude`: 纬度
- `GPSLongitude`: 经度
- `GPSAltitude`: 海拔高度

## 注意事项

1. **备份**: 默认情况下，修改 EXIF 信息时会自动创建备份文件（文件名格式：`原文件名_backup_时间戳.扩展名`）

2. **文件格式**: 目前支持 JPEG (.jpg, .jpeg)、TIFF (.tiff, .tif) 和 PNG (.png) 格式
   - **PNG 格式说明**: PNG 格式在 PNG 3.0（2023年发布）中才开始支持 EXIF 数据。大多数 PNG 图片可能不包含 EXIF 信息。如果 PNG 图片包含 EXIF，工具可以读取和修改；如果不包含，工具会显示"该图片没有 EXIF 信息"

3. **日期时间格式**: 修改日期时间字段时，请使用格式 `YYYY:MM:DD HH:MM:SS`（例如：`2025:01:01 12:00:00`）

4. **权限**: 确保对目标文件有写入权限

## 示例输出

### 文本格式
```
=== EXIF 信息 ===

[0th]
  Make: Canon
  Model: Canon EOS 5D Mark IV
  DateTime: 2025:01:01 12:00:00

[Exif]
  DateTimeOriginal: 2025:01:01 12:00:00
  ExposureTime: 1/125
  FNumber: 2.8
  ISOSpeedRatings: 400
==================================================
```

### JSON 格式
```json
{
  "0th": {
    "Make": "Canon",
    "Model": "Canon EOS 5D Mark IV",
    "DateTime": "2025:01:01 12:00:00"
  },
  "Exif": {
    "DateTimeOriginal": "2025:01:01 12:00:00",
    "ExposureTime": "1/125",
    "FNumber": "2.8",
    "ISOSpeedRatings": 400
  }
}
```

## 许可证

MIT License

