#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import process from 'node:process';
import puppeteer from 'puppeteer-core';

const ORIGIN = 'https://wenshu.court.gov.cn';
const DEFAULT_CHROME_PATHS = [
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/usr/bin/chromium-browser',
];

function printHelp() {
  console.log(`用法:
  wenshu-export <文书URL> [选项]
  wenshu-export --login

选项:
  -o, --output <file>   输出 HTML 路径（默认: ~/Downloads/<标题>.html）
      --pdf             同时导出 PDF（需 Chrome）
      --login           打开浏览器登录裁判文书网（会话会保存）
      --headed          显示浏览器窗口（调试/登录时使用）
      --timeout <ms>    等待正文加载超时（默认 90000）
  -h, --help            显示帮助

示例:
  wenshu-export "https://wenshu.court.gov.cn/website/wenshu/181107ANFZ0BXSK4/index.html?docId=..."
  wenshu-export --login
  wenshu-export "<url>" --pdf -o ~/Downloads/判决.html
`);
}

function parseArgs(argv) {
  const options = {
    url: '',
    output: '',
    pdf: false,
    login: false,
    headed: false,
    timeout: 90000,
    help: false,
  };

  const positional = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    switch (arg) {
      case '-h':
      case '--help':
        options.help = true;
        break;
      case '-o':
      case '--output':
        options.output = argv[++i] ?? '';
        break;
      case '--pdf':
        options.pdf = true;
        break;
      case '--login':
        options.login = true;
        break;
      case '--headed':
        options.headed = true;
        break;
      case '--timeout':
        options.timeout = Number(argv[++i] ?? 90000);
        break;
      default:
        if (arg.startsWith('-')) {
          throw new Error(`未知参数: ${arg}`);
        }
        positional.push(arg);
    }
  }

  options.url = positional[0] ?? '';
  return options;
}

function resolveChromePath() {
  const fromEnv = process.env.CHROME_PATH?.trim();
  if (fromEnv && fs.existsSync(fromEnv)) return fromEnv;
  for (const candidate of DEFAULT_CHROME_PATHS) {
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error('未找到 Chrome。请安装 Google Chrome，或设置环境变量 CHROME_PATH');
}

function resolveProfileDir() {
  return path.join(os.homedir(), '.config', 'wenshu-export', 'chrome-profile');
}

function sanitizeFilename(name) {
  return (name || '裁判文书').replace(/[\\/:*?"<>|]/g, '_').replace(/\s+/g, ' ').trim().slice(0, 100);
}

function buildExportHtml(pdfBoxHtml, title, origin = ORIGIN) {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${title}</title>
<link rel="stylesheet" href="${origin}/website/wenshu/css/common.css">
<link rel="stylesheet" href="${origin}/website/wenshu/css/detail.css">
<style>
  html, body { margin: 0; padding: 0; background: #eee8d8; }
  .export-wrap {
    max-width: 900px;
    margin: 24px auto;
    padding: 24px;
    background: #fff;
    box-shadow: 0 0 12px rgba(0, 0, 0, 0.08);
  }
  .detailBg .detailBox .del_center .PDF_box .PDF_pox {
    background: url(${origin}/website/wenshu/images/detail/bg_watermark.png) top center repeat-y !important;
  }
  @media print {
    html, body { background: #fff; }
    .export-toolbar { display: none !important; }
    .export-wrap { box-shadow: none; margin: 0; padding: 0; max-width: none; }
  }
</style>
</head>
<body>
<div class="export-toolbar" style="max-width:900px;margin:12px auto;padding:12px 16px;background:#fff3f3;border:1px solid #f0caca;border-radius:6px;font:14px/1.6 -apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;">
  导出说明：按 <b>Cmd/Ctrl + P</b> →「存储为 PDF」→ 勾选「背景图形」以保留水印。
</div>
<div class="export-wrap">
  <div class="detailBg">
    <div class="detailBox clearfix">
      <div class="del_center">${pdfBoxHtml}</div>
    </div>
  </div>
</div>
</body>
</html>`;
}

async function launchBrowser(chromePath, profileDir, headed) {
  fs.mkdirSync(profileDir, { recursive: true });
  return puppeteer.launch({
    executablePath: chromePath,
    headless: headed ? false : 'new',
    userDataDir: profileDir,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
    ],
    defaultViewport: { width: 1280, height: 900 },
  });
}

async function waitForDocument(page, timeoutMs) {
  await page.waitForFunction(
    () => {
      const box = document.querySelector('.PDF_box');
      if (!box) return false;
      return box.innerText.replace(/\s+/g, '').length > 200;
    },
    { timeout: timeoutMs }
  );
}

async function extractDocument(page) {
  return page.evaluate(() => {
    const pdfBox = document.querySelector('.PDF_box');
    if (!pdfBox) {
      throw new Error('未找到 .PDF_box');
    }
    const title = pdfBox.querySelector('.PDF_title')?.innerText?.trim() || document.title || '裁判文书';
    return {
      title,
      html: pdfBox.outerHTML,
      caseNo: pdfBox.querySelector('#ahdiv')?.innerText?.trim() || '',
      court: document.querySelector('.del_right')?.innerText?.slice(0, 200) || '',
    };
  });
}

async function runLogin(chromePath, profileDir) {
  const browser = await launchBrowser(chromePath, profileDir, true);
  try {
    const page = await browser.newPage();
    await page.goto(`${ORIGIN}/website/wenshu/181029CR4M5A62CH/index.html`, {
      waitUntil: 'networkidle2',
      timeout: 120000,
    });
    console.log('请在打开的浏览器中登录裁判文书网。');
    console.log('登录完成后关闭浏览器窗口，脚本会自动结束。');
    await new Promise((resolve) => browser.on('disconnected', resolve));
  } finally {
    if (browser.isConnected()) {
      await browser.close();
    }
  }
}

async function exportDocument(options) {
  const chromePath = resolveChromePath();
  const profileDir = resolveProfileDir();
  const browser = await launchBrowser(chromePath, profileDir, options.headed);

  try {
    const page = await browser.newPage();
    await page.setUserAgent(
      'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    );

    console.log('正在打开文书页面...');
    await page.goto(options.url, { waitUntil: 'networkidle2', timeout: 120000 });

    console.log('等待正文加载...');
    try {
      await waitForDocument(page, options.timeout);
    } catch {
      const snippet = await page.evaluate(() => document.body?.innerText?.slice(0, 300) || '');
      throw new Error(
        `正文未加载。可能未登录或无阅读权限。\n当前页面片段: ${snippet}\n建议先运行: wenshu-export --login`
      );
    }

    const doc = await extractDocument(page);
    const exportHtml = buildExportHtml(doc.html, doc.title);

    const outputHtml = options.output
      ? path.resolve(options.output)
      : path.join(os.homedir(), 'Downloads', `${sanitizeFilename(doc.title)}.html`);

    fs.mkdirSync(path.dirname(outputHtml), { recursive: true });
    fs.writeFileSync(outputHtml, exportHtml, 'utf8');

    console.log(`标题: ${doc.title}`);
    if (doc.caseNo) console.log(`案号: ${doc.caseNo}`);
    console.log(`HTML: ${outputHtml}`);

    if (options.pdf) {
      const pdfPath = outputHtml.replace(/\.html?$/i, '') + '.pdf';
      const pdfPage = await browser.newPage();
      await pdfPage.setContent(exportHtml, { waitUntil: 'networkidle0', timeout: 120000 });
      await pdfPage.pdf({
        path: pdfPath,
        format: 'A4',
        printBackground: true,
        margin: { top: '20mm', right: '15mm', bottom: '20mm', left: '15mm' },
      });
      console.log(`PDF:  ${pdfPath}`);
    }

    return outputHtml;
  } finally {
    await browser.close();
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }

  if (options.login) {
    await runLogin(resolveChromePath(), resolveProfileDir());
    console.log('登录会话已保存。');
    return;
  }

  if (!options.url) {
    printHelp();
    process.exit(1);
  }

  if (!options.url.includes('wenshu.court.gov.cn')) {
    throw new Error('请提供裁判文书网文书全文页 URL');
  }

  await exportDocument(options);
}

main().catch((err) => {
  console.error(`错误: ${err.message}`);
  process.exit(1);
});
