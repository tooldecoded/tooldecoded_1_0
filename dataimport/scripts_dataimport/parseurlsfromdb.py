#!/usr/bin/env python3
import os
import sys
import re
import csv
import django
from urllib.parse import urlparse

# -------------------------------------------------------------------
# Django setup
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tooldecoded.settings")
django.setup()

from toolanalysis.models import PriceListings  # noqa: E402

# -------------------------------------------------------------------
# SKU extraction helpers
# -------------------------------------------------------------------
PATTERN_TWO_SEG = r"\b\d{4,}[A-Za-z]*-\d+[A-Za-z]*\b"       # 2525-20, 2641-20CT, 3107-6
PATTERN_THREE_SEG = r"\b\d{2}-\d{2}-\d+[A-Za-z]*\b"         # 48-22-2610, 49-66-6806
COMBINED_RE = re.compile(f"(?:{PATTERN_THREE_SEG})|(?:{PATTERN_TWO_SEG})")

def extract_slug(url: str) -> str | None:
    """Return the product slug (the segment before the last slash)."""
    segs = [s for s in urlparse(url).path.split("/") if s]
    return segs[-2] if len(segs) >= 2 else None

def extract_skus_in_order(slug: str) -> list[str]:
    """Return all SKUs found in slug, preserving order and uniqueness."""
    if not slug:
        return []
    matches = [m.group(0) for m in COMBINED_RE.finditer(slug)]
    seen, ordered = set(), []
    for m in matches:
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    return ordered

# -------------------------------------------------------------------
# Main logic
# -------------------------------------------------------------------
def main():
    print("🔄 Fetching PriceListings from database...")

    pricelistings = PriceListings.objects.all()
    rows = []
    max_skus = 0

    for record in pricelistings:
        url = getattr(record, "url", "") or ""
        price = getattr(record, "price", "") or ""
        currency = getattr(record, "currency", "") or ""
        retailer_sku = getattr(record, "retailer_sku", "") or ""
        datepulled = getattr(record, "datepulled", "") or ""

        slug = extract_slug(url)
        skus = extract_skus_in_order(slug or "")
        max_skus = max(max_skus, len(skus))

        rows.append({
            "url": url,
            "price": price,
            "currency": currency,
            "retailer_sku": retailer_sku,
            "datepulled": datepulled,
            "skus": skus,
        })

    # Build header
    header = ["url", "price", "currency", "retailer_sku", "datepulled"] + [
        f"sku{i}" for i in range(1, max_skus + 1)
    ]

    # Save automatically to project root
    output_path = os.path.join(BASE_DIR, "exported_pricelistings.csv")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            padded_skus = row["skus"] + [""] * (max_skus - len(row["skus"]))
            writer.writerow([
                row["url"],
                row["price"],
                row["currency"],
                row["retailer_sku"],
                row["datepulled"],
                *padded_skus,
            ])

    print(f"✅ Export complete. File saved to:\n{output_path}")

if __name__ == "__main__":
    main()
