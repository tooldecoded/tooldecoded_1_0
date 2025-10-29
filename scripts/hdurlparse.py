#!/usr/bin/env python3
import sys
import re
import csv
from urllib.parse import urlparse

# --- SKU Patterns ---
PATTERN_TWO_SEG = r'\b\d{4,}[A-Za-z]*-\d+[A-Za-z]*\b'      # e.g. 2525-20, 2641-20CT, 3107-6
PATTERN_THREE_SEG = r'\b\d{2}-\d{2}-\d+[A-Za-z]*\b'        # e.g. 48-22-2610, 49-66-6806
COMBINED_RE = re.compile(f'(?:{PATTERN_THREE_SEG})|(?:{PATTERN_TWO_SEG})')

def extract_slug(url: str) -> str | None:
    """Grab the product slug (second-to-last path segment) from a Home Depot URL"""
    segs = [s for s in urlparse(url).path.split('/') if s]
    return segs[-2] if len(segs) >= 2 else None

def extract_skus_in_order(slug: str) -> list[str]:
    """Extract all SKUs from the slug, preserving order and uniqueness"""
    matches = [m.group(0) for m in COMBINED_RE.finditer(slug or "")]
    seen, ordered = set(), []
    for m in matches:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered

# --- EDIT THIS PART ---
# Path to the file that contains your URLs (one per line)
URL_FILE = "urls.txt"
# --- STOP EDITING ---

def main():
    # Read URLs from file instead of stdin/args
    try:
        with open(URL_FILE, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        sys.exit(f"❌ URL file not found: {URL_FILE}")

    rows = []
    max_skus = 0

    for url in urls:
        slug = extract_slug(url)
        skus = extract_skus_in_order(slug or "")
        max_skus = max(max_skus, len(skus))
        rows.append((url, skus))

    # Build header: URL, SKU1..SKU_n
    header = ["url"] + [f"sku{i}" for i in range(1, max_skus + 1)]

    # Print directly to terminal for now
    writer = csv.writer(sys.stdout)
    writer.writerow(header)
    for url, skus in rows:
        padded = skus + [""] * (max_skus - len(skus))
        writer.writerow([url] + padded)

if __name__ == "__main__":
    main()
