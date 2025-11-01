"""Django management command to inspect manufacturer product pages and identify HTML selectors."""

import json
import re
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Inspect a manufacturer product page to identify HTML structure and CSS selectors"

    def add_arguments(self, parser):
        parser.add_argument("url", type=str, help="Manufacturer product page URL to inspect")

    def handle(self, *args, **options):
        url = options["url"]
        
        self.stdout.write(self.style.SUCCESS(f"Fetching URL: {url}"))
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=(10, 30), allow_redirects=True)
            response.raise_for_status()
        except requests.exceptions.Timeout as e:
            self.stdout.write(self.style.ERROR(f"Request timed out: {e}. Try again or check your connection."))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch URL: {e}"))
            return
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        self.stdout.write(self.style.SUCCESS("\n=== HTML STRUCTURE ANALYSIS ===\n"))
        
        # Find title
        self.stdout.write("--- PRODUCT NAME ---")
        for selector in ['h1', 'h2.product-title', '.product-title', '[data-product-title]', 'title']:
            elements = soup.select(selector)
            if elements:
                text = elements[0].get_text(strip=True)
                self.stdout.write(f"  {selector}: {text[:100]}")
                if elements[0].get('class'):
                    self.stdout.write(f"    Classes: {elements[0].get('class')}")
                if elements[0].get('id'):
                    self.stdout.write(f"    ID: {elements[0].get('id')}")
        
        # Find breadcrumb
        self.stdout.write("\n--- BREADCRUMB ---")
        for selector in ['nav[aria-label*="Breadcrumb"]', 'nav.breadcrumb', 'ol.breadcrumb', '[data-breadcrumb]', '.breadcrumb', 'nav']:
            elements = soup.select(selector)
            for el in elements[:2]:
                text = el.get_text()
                if 'home' in text.lower() and any(word in text.lower() for word in ['product', 'tools', 'drill']):
                    self.stdout.write(f"  {selector}: {text[:200]}")
                    if el.get('class'):
                        self.stdout.write(f"    Classes: {el.get('class')}")
                    break
        
        # Find specifications table
        self.stdout.write("\n--- SPECIFICATIONS ---")
        tables = soup.find_all('table')
        for i, table in enumerate(tables[:3]):
            rows = table.find_all('tr')
            if rows:
                sample_row = rows[0]
                cells = sample_row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    self.stdout.write(f"  Table #{i+1}: Found {len(rows)} rows")
                    if table.get('class'):
                        self.stdout.write(f"    Classes: {table.get('class')}")
                    if table.get('id'):
                        self.stdout.write(f"    ID: {table.get('id')}")
                    # Show sample data
                    for row in rows[:3]:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            key = cells[0].get_text(strip=True)
                            value = cells[1].get_text(strip=True)
                            if key and value:
                                self.stdout.write(f"    Sample: {key} = {value}")
        
        # Find features/bullets
        self.stdout.write("\n--- FEATURES/BULLETS ---")
        bullets_found = []
        for selector in ['ul li', '[class*="feature"]', '[class*="bullet"]', '[class*="benefit"]']:
            elements = soup.select(selector)
            for el in elements[:10]:
                text = el.get_text(strip=True)
                if len(text) > 20 and text not in bullets_found:
                    bullets_found.append(text)
                    if len(bullets_found) <= 3:
                        self.stdout.write(f"  {selector}: {text[:100]}")
                        if el.get('class'):
                            self.stdout.write(f"    Classes: {el.get('class')}")
                        if el.parent and el.parent.get('class'):
                            self.stdout.write(f"    Parent classes: {el.parent.get('class')}")
        
        # Find included items
        self.stdout.write("\n--- INCLUDED ITEMS ---")
        includes_headings = soup.find_all(['h2', 'h3', 'h4', 'h5'], string=lambda t: t and 'include' in t.lower() if t else False)
        for heading in includes_headings[:2]:
            self.stdout.write(f"  Found heading: {heading.get_text(strip=True)}")
            parent = heading.find_parent()
            if parent:
                items = parent.find_all(['li', 'div', 'span'])
                for item in items[:5]:
                    text = item.get_text(strip=True)
                    if text and len(text) > 3 and text not in ['Includes', 'Included in the Box']:
                        self.stdout.write(f"    Item: {text}")
                        if item.get('class'):
                            self.stdout.write(f"      Classes: {item.get('class')}")
        
        # Find description
        self.stdout.write("\n--- DESCRIPTION ---")
        for selector in ['[class*="description"]', '[class*="overview"]', '[data-description]', '.product-overview', '.product-description']:
            elements = soup.select(selector)
            if elements:
                text = elements[0].get_text(strip=True)
                if len(text) > 50:
                    self.stdout.write(f"  {selector}: {text[:200]}")
                    if elements[0].get('class'):
                        self.stdout.write(f"    Classes: {elements[0].get('class')}")
        
        # Find product images
        self.stdout.write("\n--- PRODUCT IMAGES ---")
        img_selectors = [
            ('img[src*="product"]', 'product in src'),
            (f'img[alt*="{url.split("/")[-2]}" if "/" in url else ""]', 'SKU in alt'),
            ('.product-image img', 'product-image class'),
            ('[data-product-image] img', 'data-product-image attribute'),
        ]
        found_images = []
        for selector, description in img_selectors:
            try:
                elements = soup.select(selector)
                for img in elements[:3]:
                    src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                    if src and src not in found_images:
                        found_images.append(src)
                        self.stdout.write(f"  {description}: {src[:100]}")
                        if img.get('class'):
                            self.stdout.write(f"    Classes: {img.get('class')}")
            except:
                pass
        
        # Extract SKU from URL
        self.stdout.write("\n--- SKU EXTRACTION ---")
        sku_match = re.search(r'/product/([^/]+)/?', url)
        if sku_match:
            sku = sku_match.group(1).upper()
            self.stdout.write(f"  From URL pattern: {sku}")
        
        # Summary
        self.stdout.write(self.style.SUCCESS("\n=== SUGGESTED SELECTORS ===\n"))
        self.stdout.write("Use the above information to create CSS selectors in your parser.")
        self.stdout.write("Test selectors with: soup.select('your-selector-here')")

