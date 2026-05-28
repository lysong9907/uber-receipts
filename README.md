# Uber Receipts Downloader

Download real Uber trip receipts from Gmail, filter out useless charge summary emails, extract trip times, and save as PDF, PNG, or HTML files — ready for reimbursement.

## Features

- 🔍 **Auto-search** Gmail for Uber receipt emails
- 🚫 **Smart filter** — automatically skips charge summary emails (not useful for reimbursement)
- ⏰ **Time extraction** — pulls trip date/time from receipt HTML and uses it as filename
- 📄 **PDF/PNG/HTML** output — renders receipts via Chrome headless for pixel-perfect results
- 🔄 **Safe re-run** — existing files are overwritten, no duplicates

## Prerequisites

- Python 3.x
- Google Chrome (or Chromium) — for PDF/PNG rendering via headless mode
- `imap-smtp-email` skill (for Gmail access)

## Usage

### 1. Get email credentials

```bash
bash 'get-token.sh'
```

This auto-detects the bound email and writes credentials to `.env`.

### 2. Download receipts

```bash
python3 scripts/download_receipts.py \
  --account-email 'your-email@gmail.com' \
  --output-dir './receipts' \
  --since '2025-01-01' \
  --format pdf
```

### Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--account-email` | Yes | Gmail account to search |
| `--output-dir` | Yes | Directory to save receipt files |
| `--since` | No | Only fetch emails on or after YYYY-MM-DD |
| `--format` | No | Output format: `pdf` (default), `png`, `html`, or `all` |
| `--email-gateway` | No | Custom path to `email_gateway.sh` (auto-detected by default) |

### Format Options

- **`pdf`** (default): Renders each receipt as a PDF via Chrome headless
- **`png`**: Renders each receipt as a PNG screenshot (800×1200)
- **`html`**: Saves the raw HTML email body
- **`all`**: Saves all three formats for each receipt

### Example

```bash
# Download all Uber receipts since May 1st as PDF
python3 scripts/download_receipts.py \
  --account-email 'user@gmail.com' \
  --output-dir './receipts' \
  --since '2025-05-01' \
  --format pdf

# Download as PNG images
python3 scripts/download_receipts.py \
  --account-email 'user@gmail.com' \
  --output-dir './receipts' \
  --format png

# Save all formats (HTML + PDF + PNG)
python3 scripts/download_receipts.py \
  --account-email 'user@gmail.com' \
  --output-dir './receipts' \
  --format all
```

## How It Works

1. Searches inbox for emails with subject "Uber"
2. For each email:
   - Fetches the full email body
   - Skips if it's a charge summary (contains `uber_logo_charge_summary`)
   - Extracts the trip date and time from the HTML content
   - Saves in the requested format via Chrome headless rendering
3. Prints a summary of downloaded vs skipped files

## Output

Files are named like:
```
Uber_4576_May_19_2026_7_32_AM.pdf
Uber_4592_May_20_2026_11_04_AM.png
Uber_4625_May_22_2026_4_26_PM.html
```

The UID prefix prevents collisions when multiple trips have the same time.

## Notes

- Charge summary emails are automatically filtered out
- If Chrome is not found or conversion fails, falls back to HTML
- Re-running is safe — existing files are overwritten
