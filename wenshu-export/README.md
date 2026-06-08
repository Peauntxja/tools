# wenshu-export

从中国裁判文书网导出**带水印样式**的文书 HTML（可选 PDF）。

> 说明：工具导出的是页面已渲染的正文，不绕过下载权限校验。需能正常阅读全文；若提示无权限下载，仍可用本工具导出 HTML 后本地打印为 PDF。

## 依赖

- Node.js 18+
- Google Chrome（macOS 默认路径已内置）

## 安装

```bash
cd /Users/kusuri_mizuki/myProject/tools/wenshu-export
chmod +x wenshu-export
npm install
```

可选：加入 PATH

```bash
ln -sf /Users/kusuri_mizuki/myProject/tools/wenshu-export/wenshu-export ~/.local/bin/wenshu-export
```

## 首次使用：登录

```bash
./wenshu-export --login
```

在打开的 Chrome 中登录裁判文书网，完成后关闭浏览器。会话保存在 `~/.config/wenshu-export/chrome-profile`。

## 导出文书

```bash
./wenshu-export "https://wenshu.court.gov.cn/website/wenshu/181107ANFZ0BXSK4/index.html?docId=..."
```

同时导出 PDF：

```bash
./wenshu-export "<文书URL>" --pdf
```

指定输出路径：

```bash
./wenshu-export "<文书URL>" -o ~/Downloads/我的判决.html --pdf
```

## 给 Cursor / AI 用

下次直接发文书链接，并说明：

> 用 `wenshu-export` 导出 HTML

命令示例：

```bash
/Users/kusuri_mizuki/myProject/tools/wenshu-export/wenshu-export "<url>" --pdf
```

## 常见问题

| 问题 | 处理 |
|------|------|
| 正文未加载 | 先 `--login`，确认浏览器里能打开该文书 |
| 水印 PDF 不显示 | 打开 HTML 后 `Cmd+P`，勾选「背景图形」 |
| 找不到 Chrome | 设置 `export CHROME_PATH=/path/to/chrome` |
