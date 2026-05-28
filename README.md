# Uber Receipts Downloader — Uber 行程收据下载器

从 Gmail 邮箱自动下载 Uber 行程收据，过滤无效的计费汇总邮件，提取行程时间，并保存为 **PDF**、**PNG** 或 **HTML** 格式，方便直接用于报销。

## ✨ 功能特性

- 🔍 **自动搜索** Gmail 中的 Uber 收据邮件
- 🚫 **智能过滤** — 自动跳过计费汇总邮件（不可用于报销）
- ⏰ **时间提取** — 从收据 HTML 中解析行程日期和时间，自动用作文件名
- 📄 **多格式输出** — 通过 Chrome 无头模式渲染，PDF/PNG 像素级还原原始收据
- 🔄 **安全重试** — 支持重复运行，已有文件会被覆盖，不会产生重复

## 📋 前置要求

- Python 3.x
- Google Chrome（或 Chromium）— 用于通过无头模式渲染 PDF/PNG
- `imap-smtp-email` 技能（用于 Gmail 访问）

## 🚀 使用方法

### 1. 获取邮箱凭证

```bash
bash 'get-token.sh'
```

该脚本会自动检测已绑定的邮箱，并将凭证写入 `.env` 文件。

### 2. 下载收据

```bash
python3 scripts/download_receipts.py \
  --account-email 'your-email@gmail.com' \
  --output-dir './receipts' \
  --since '2025-01-01' \
  --format pdf
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--account-email` | ✅ | 要搜索的 Gmail 邮箱账号 |
| `--output-dir` | ✅ | 保存收据文件的目录 |
| `--since` | 否 | 仅获取该日期及之后的邮件（格式 YYYY-MM-DD） |
| `--format` | 否 | 输出格式：`pdf`（默认）、`png`、`html` 或 `all` |
| `--email-gateway` | 否 | 自定义 `email_gateway.sh` 路径（默认自动检测） |

### 格式选项

- **`pdf`**（默认）：通过 Chrome 无头模式将每份收据渲染为 PDF 文件，适合打印和归档
- **`png`**：将每份收据渲染为 PNG 截图（800×1200 窗口），适合快速分享
- **`html`**：保存原始 HTML 邮件内容，适合手动查看
- **`all`**：为每份收据同时保存三种格式（HTML + PDF + PNG）

### 使用示例

```bash
# 下载 5 月 1 日以来的所有 Uber 收据，保存为 PDF
python3 scripts/download_receipts.py \
  --account-email 'user@gmail.com' \
  --output-dir './receipts' \
  --since '2025-05-01' \
  --format pdf

# 下载为 PNG 图片
python3 scripts/download_receipts.py \
  --account-email 'user@gmail.com' \
  --output-dir './receipts' \
  --format png

# 同时保存所有格式（HTML + PDF + PNG）
python3 scripts/download_receipts.py \
  --account-email 'user@gmail.com' \
  --output-dir './receipts' \
  --format all
```

## 📖 工作原理

1. 在收件箱中搜索主题为 "Uber" 的邮件
2. 对每封邮件：
   - 获取完整的邮件正文
   - 如果是计费汇总邮件（包含 `uber_logo_charge_summary`），自动跳过
   - 从 HTML 内容中提取行程日期和时间
   - 通过 Chrome 无头模式渲染为指定格式并保存
3. 打印下载摘要（已下载数 vs 已跳过数）

## 📁 输出示例

文件命名格式：
```
Uber_4576_May_19_2026_7_32_AM.pdf
Uber_4592_May_20_2026_11_04_AM.png
Uber_4625_May_22_2026_4_26_PM.html
```

UID 前缀用于防止多趟行程时间相同时的文件名冲突。

## ⚠️ 注意事项

- 计费汇总邮件会自动过滤，不会下载
- 如果找不到 Chrome 或转换失败，会自动降级保存为 HTML
- 重复运行是安全的 — 已有文件会被覆盖
