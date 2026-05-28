---
name: uber-receipts
description: "Download Uber trip receipt emails from the user's Gmail inbox for reimbursement purposes. Searches for Uber emails, filters out useless charge summary emails, downloads real receipts, extracts trip time from HTML, and saves as PDF/PNG/HTML. Use when the user asks to download Uber receipts, export Uber trips for reimbursement, grab Uber行程/收据/报销, or similar requests involving Uber ride receipts."
---

# Uber Receipts Downloader

Download real Uber trip receipts (not charge summaries) from Gmail, extract trip times, and save as PDF, PNG, or HTML files ready for reimbursement.

## Prerequisites

- `imap-smtp-email` skill must be installed
- Google Chrome installed (for PDF/PNG conversion via headless mode)
- Run `get-token.sh` first to obtain email credentials before calling the download script

## Workflow

### Step 1: Get email credentials

```bash
bash '~/.qclaw/skills/imap-smtp-email/get-token.sh'
```

This auto-detects the bound email and writes credentials to `.env`.

### Step 2: Download receipts

```bash
python3 '~/.qclaw/skills/uber-receipts/scripts/download_receipts.py' \
  --account-email 'USER_EMAIL' \
  --output-dir '~/Documents/reimbursement' \
  --since '2026-05-15' \
  --format pdf
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--account-email` | Yes | The Gmail account to search |
| `--output-dir` | Yes | Directory to save receipt files |
| `--since` | No | Only fetch emails on or after YYYY-MM-DD |
| `--format` | No | Output format: `pdf` (default), `png`, `html`, or `all` |
| `--keep-html` | No | Keep intermediate HTML files when converting |
| `--email-gateway` | No | Custom path to email_gateway.sh (auto-detected by default) |

### Format Options

- **`pdf`** (default): Renders each receipt as a PDF file using Chrome headless. Best for printing and archiving.
- **`png`**: Renders each receipt as a PNG screenshot (800x1200 window). Best for quick image sharing.
- **`html`**: Saves the raw HTML email body (original behavior). Useful for manual review.
- **`all`**: Saves all three formats (HTML + PDF + PNG) for each receipt.

### What the script does

1. Searches inbox for emails with subject "Uber"
2. Filters by date if `--since` is provided
3. For each email:
   - Fetches the full email body
   - Skips if it contains `uber_logo_charge_summary` (charge summary, not useful for reimbursement)
   - Extracts the trip date and time from the HTML content
   - Saves in the requested format (PDF/PNG/HTML) via Chrome headless
4. Prints a summary of downloaded vs skipped files

### Output format

Files are named like:
```
Uber_4576_May_19_2026_7_32_AM.pdf
Uber_4592_May_20_2026_11_04_AM.png
Uber_4625_May_22_2026_4_26_PM.html
```

The UID is included to avoid collisions when multiple trips have the same time.

### Important notes

- Charge summary emails (Uber's periodic billing summaries) are automatically filtered out by checking for `uber_logo_charge_summary` in the HTML body
- PDF/PNG conversion uses Google Chrome headless mode — Chrome must be installed
- If Chrome is not found or conversion fails, falls back to saving as HTML
- If the download is interrupted, re-running is safe — existing files are overwritten
