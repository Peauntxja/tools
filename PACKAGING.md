# 打包说明

## 前置要求

- Python 3.10+
- `pip install -r requirements.txt`

## macOS

```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

产物：`dist/图片格式转换工具.app`（可选 DMG）

## Windows

```cmd
scripts\build_windows.bat
```

产物：`dist\图片格式转换工具\图片格式转换工具.exe`

## GitHub Actions

推送版本标签触发双平台构建：

```bash
git tag v1.0.0
git push origin v1.0.0
```

在 Releases 页面下载对应平台的 zip。
