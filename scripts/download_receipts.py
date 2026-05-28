#!/usr/bin/env python3
"""
Download Uber receipt emails from Gmail via email_gateway.sh.
Filters out charge summary emails, downloads real receipts,
extracts trip time from HTML, and saves as PDF/PNG/HTML.

Usage:
    python3 download_receipts.py --account-email EMAIL --output-dir DIR [--since YYYY-MM-DD] [--format pdf|png|html|all] [--email-gateway PATH]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    """Extract visible text from HTML."""
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {'style', 'script', 'meta', 'link', 'head'}
        self.in_skip = False

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.in_skip = True

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.in_skip = False

    def handle_data(self, data):
        if not self.in_skip:
            t = data.strip()
            if t:
                self.text.append(t)


def extract_text(html_content):
    parser = TextExtractor()
    parser.feed(html_content)
    return '\n'.join(parser.text)


def is_charge_summary(html_content):
    """Check if this email is a charge summary (useless for reimbursement)."""
    return 'uber_logo_charge_summary' in html_content


def find_trip_time(html_content):
    """Extract trip date and time from Uber receipt HTML."""
    parser = TextExtractor()
    parser.feed(html_content)
    full_text = ' '.join(parser.text)

    # Pattern: "May 23, 2026 9:52 PM" or "May 23, 2026 , 9:52 PM"
    m = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*20\d{2}\s*,?\s*(\d{1,2}:\d{2}\s*[AP]M)',
        full_text
    )
    if m:
        month = m.group(1)
        day = m.group(2)
        time = m.group(3)
        return f"{month}_{day}_2026_{time.replace(':', '_').replace(' ', '_')}"

    # Fallback: just find date
    m = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*20\d{2}',
        full_text
    )
    if m:
        return f"{m.group(1)}_{m.group(2)}_2026"

    return "unknown_date"


def sanitize_filename(name):
    """Remove characters unsafe for filenames."""
    return re.sub(r'[<>:"/\\|?*]', '_', name)


def find_chrome():
    """Find Chrome executable path."""
    candidates = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # Try PATH
    for name in ['google-chrome', 'chromium', 'chromium-browser', 'chrome']:
        try:
            result = subprocess.run(['which', name], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
    return None


def convert_html(html_content, output_path, fmt, window_size=(800, 1200)):
    """
    Convert HTML to PDF or PNG using Chrome headless.
    Returns True on success, False on failure.
    """
    chrome_path = find_chrome()
    if not chrome_path:
        print("  Warning: Chrome not found, skipping conversion", file=sys.stderr)
        return False

    # Write HTML to a temp file for Chrome to read
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        tmp_html = f.name

    try:
        file_url = f'file://{tmp_html}'
        cmd = [
            chrome_path,
            '--headless=new', '--no-sandbox', '--disable-gpu',
        ]

        if fmt == 'pdf':
            cmd += ['--print-to-pdf=' + output_path, file_url]
        elif fmt == 'png':
            cmd += [
                '--screenshot=' + output_path,
                f'--window-size={window_size[0]},{window_size[1]}',
                file_url,
            ]
        else:
            return False

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        # Chrome writes progress info to stderr like "X bytes written to file ..."
        # Check if output file was created
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        else:
            print(f"  Conversion failed: {result.stderr.strip()}", file=sys.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("  Conversion timed out", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  Conversion error: {e}", file=sys.stderr)
        return False
    finally:
        try:
            os.unlink(tmp_html)
        except Exception:
            pass


def run_gateway(args, timeout=30):
    """Run email_gateway.sh with given args."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1


def search_uber_emails(email_gateway, account_email, days=30, limit=50):
    """Search for Uber emails and return list of (uid, date, subject, snippet)."""
    stdout, stderr, rc = run_gateway([
        email_gateway, 'inbox-search',
        '--account-email', account_email,
        '--subject', 'Uber',
        '--recent', f'{days}d',
        '--limit', str(limit)
    ], timeout=45)

    if rc != 0:
        print(f"Search failed: {stderr}", file=sys.stderr)
        return []

    # Parse JSON from output
    start = stdout.find('[')
    end = stdout.rfind(']') + 1
    if start < 0:
        print("No JSON found in search output", file=sys.stderr)
        return []

    try:
        emails = json.loads(stdout[start:end])
    except json.JSONDecodeError:
        print("Failed to parse search output", file=sys.stderr)
        return []

    return emails


def fetch_email(email_gateway, account_email, uid):
    """Fetch a single email by UID, return body HTML."""
    stdout, stderr, rc = run_gateway([
        email_gateway, 'inbox-fetch',
        '--account-email', account_email,
        str(uid)
    ], timeout=30)

    if rc != 0:
        print(f"  Fetch failed UID {uid}: {stderr}", file=sys.stderr)
        return None

    start = stdout.find('{')
    end = stdout.rfind('}') + 1
    if start < 0:
        return None

    try:
        obj = json.loads(stdout[start:end])
        return obj.get('body', obj.get('html', ''))
    except json.JSONDecodeError:
        return None


def filter_by_date(emails, since_date):
    """Filter emails to only those on or after since_date."""
    if not since_date:
        return emails

    filtered = []
    for e in emails:
        date_str = e.get('date', '')
        if date_str and date_str[:10] >= since_date:
            filtered.append(e)
    return filtered


def main():
    parser = argparse.ArgumentParser(description='Download Uber receipt emails for reimbursement')
    parser.add_argument('--account-email', required=True, help='Email account to search')
    parser.add_argument('--output-dir', required=True, help='Directory to save receipts')
    parser.add_argument('--since', default=None, help='Only fetch emails since YYYY-MM-DD')
    parser.add_argument('--format', choices=['html', 'pdf', 'png', 'all'], default='pdf',
                        help='Output format: html, pdf, png, or all (default: pdf)')
    parser.add_argument('--keep-html', action='store_true',
                        help='Keep intermediate HTML files (useful when converting to pdf/png)')
    parser.add_argument('--email-gateway', default=None, help='Path to email_gateway.sh')
    args = parser.parse_args()

    # Default email_gateway path
    if not args.email_gateway:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        skill_dir = os.path.dirname(script_dir)
        args.email_gateway = os.path.join(
            os.path.expanduser('~'),
            '.qclaw', 'skills', 'imap-smtp-email',
            'scripts', 'unix', 'email_gateway.sh'
        )

    if not os.path.exists(args.email_gateway):
        print(f"Error: email_gateway.sh not found at {args.email_gateway}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # Step 1: Search for Uber emails
    print(f"Searching for Uber emails (since {args.since or 'all time'})...")
    emails = search_uber_emails(args.email_gateway, args.account_email)
    if not emails:
        print("No Uber emails found.")
        sys.exit(0)

    # Step 2: Filter by date
    emails = filter_by_date(emails, args.since)
    print(f"Found {len(emails)} Uber emails after {args.since}")

    # Step 3: Download and filter
    downloaded = 0
    skipped_charge = 0
    results = []

    for e in emails:
        uid = e.get('uid', '')
        date = e.get('date', '')
        subject = e.get('subject', '')

        if not uid:
            continue

        # Fetch email body
        print(f"  Fetching UID {uid}...", end=' ')
        body = fetch_email(args.email_gateway, args.account_email, uid)
        if not body:
            print("FAILED")
            continue

        # Skip charge summaries
        if is_charge_summary(body):
            print("SKIP (charge summary)")
            skipped_charge += 1
            continue

        # Extract trip time
        trip_time = find_trip_time(body)
        safe_subject = sanitize_filename(subject) if subject else 'uber_receipt'

        # Determine output files based on format
        saved_files = []

        if args.format == 'html':
            filename = f"Uber_{uid}_{trip_time}.html"
            filepath = os.path.join(args.output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(body)
            saved_files.append(filename)

        elif args.format == 'pdf':
            pdf_filename = f"Uber_{uid}_{trip_time}.pdf"
            pdf_path = os.path.join(args.output_dir, pdf_filename)
            ok = convert_html(body, pdf_path, 'pdf')
            if ok:
                saved_files.append(pdf_filename)
            else:
                # Fallback: save as HTML
                html_filename = f"Uber_{uid}_{trip_time}.html"
                html_path = os.path.join(args.output_dir, html_filename)
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(body)
                saved_files.append(html_filename + ' (fallback, conversion failed)')

        elif args.format == 'png':
            png_filename = f"Uber_{uid}_{trip_time}.png"
            png_path = os.path.join(args.output_dir, png_filename)
            ok = convert_html(body, png_path, 'png')
            if ok:
                saved_files.append(png_filename)
            else:
                # Fallback: save as HTML
                html_filename = f"Uber_{uid}_{trip_time}.html"
                html_path = os.path.join(args.output_dir, html_filename)
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(body)
                saved_files.append(html_filename + ' (fallback, conversion failed)')

        elif args.format == 'all':
            # Save HTML first
            html_filename = f"Uber_{uid}_{trip_time}.html"
            html_path = os.path.join(args.output_dir, html_filename)
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(body)
            saved_files.append(html_filename)

            # Then convert to PDF
            pdf_filename = f"Uber_{uid}_{trip_time}.pdf"
            pdf_path = os.path.join(args.output_dir, pdf_filename)
            if convert_html(body, pdf_path, 'pdf'):
                saved_files.append(pdf_filename)

            # Then convert to PNG
            png_filename = f"Uber_{uid}_{trip_time}.png"
            png_path = os.path.join(args.output_dir, png_filename)
            if convert_html(body, png_path, 'png'):
                saved_files.append(png_filename)

        print(f"OK -> {', '.join(saved_files)}")
        downloaded += 1
        results.append((uid, trip_time, saved_files))

    # Summary
    print(f"\n=== Summary ===")
    print(f"Downloaded: {downloaded} receipts")
    print(f"Skipped (charge summary): {skipped_charge}")
    print(f"Saved to: {args.output_dir}")

    if results:
        print(f"\nFiles:")
        for uid, time, fnames in results:
            for fname in fnames:
                print(f"  {fname}")


if __name__ == '__main__':
    main()
