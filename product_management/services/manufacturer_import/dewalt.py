"""DEWALT product page parser."""

import re
import time
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

from .base import ManufacturerParser, ParsedProductData


class DewaltParser(ManufacturerParser):
    """Parser for DEWALT product pages."""
    
    def detect_manufacturer(self, url: str) -> str:
        """Detect if URL is for DEWALT."""
        return "DEWALT" if self.validate_url(url) else ""
    
    def validate_url(self, url: str) -> bool:
        """Check if URL is a valid DEWALT product page."""
        return 'dewalt.com' in url.lower() and '/product/' in url.lower()
    
    def parse(self, url: str) -> ParsedProductData:
        """Parse DEWALT product page."""
        data = ParsedProductData(source_url=url, brand="DEWALT")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Retry logic for network issues
        max_retries = 3
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Increased timeout for slower connections, with separate connect and read timeouts
                # Connect timeout: 10s, Read timeout: 45s (increased from 30s for slow pages)
                response = requests.get(
                    url, 
                    headers=headers, 
                    timeout=(10, 45), 
                    allow_redirects=True,
                    verify=True  # SSL verification
                )
                response.raise_for_status()
                # Success - break out of retry loop
                break
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # Wait before retrying (exponential backoff)
                    time.sleep(2 ** attempt)  # 1s, 2s, 4s delays
                    continue
                else:
                    data.add_error(
                        f"Request timed out after {max_retries} attempts. "
                        f"The website may be slow or unresponsive. Please try again in a moment."
                    )
                    return data
            except requests.exceptions.SSLError as e:
                data.add_error(f"SSL verification failed: {str(e)}")
                return data
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    data.add_error(
                        f"Connection failed after {max_retries} attempts. "
                        f"Please check your internet connection and try again."
                    )
                    return data
            except requests.exceptions.RequestException as e:
                data.add_error(f"Failed to fetch URL: {str(e)}")
                return data
            except Exception as e:
                data.add_error(f"Unexpected error fetching URL: {str(e)}")
                return data
        else:
            # This should not happen, but handle it just in case
            data.add_error(f"Failed to fetch URL after {max_retries} attempts: {str(last_exception)}")
            return data
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract product name from h1
        h1 = soup.find('h1')
        if h1:
            product_name = h1.get_text(strip=True)
            # Remove "New" prefix if present
            data.product_name = re.sub(r'^\s*New\s+', '', product_name, flags=re.IGNORECASE)
        else:
            # Fallback to title tag
            title_tag = soup.find('title')
            if title_tag:
                data.product_name = title_tag.get_text(strip=True).split('|')[0].strip()
        
        # Extract SKU from URL pattern: /product/{SKU}/
        sku_match = re.search(r'/product/([^/]+)/?', url)
        if sku_match:
            data.sku = sku_match.group(1).upper()
        
        # Extract specifications from table
        spec_table = soup.find('table')
        if spec_table:
            rows = spec_table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        data.specifications[key] = value
        
        # Extract features - look for structured feature sections
        main_content = soup.find('main') or soup.find('div', class_=re.compile(r'product|content', re.I))
        if main_content:
            # Find bullet points in lists
            bullets = main_content.find_all('li')
            for bullet in bullets:
                text = bullet.get_text(strip=True)
                # Look for feature-like bullets (usually longer text with keywords)
                if len(text) > 20:
                    # Check if it looks like a feature (has action words, benefits, etc.)
                    feature_keywords = ['capability', 'feature', 'reach', 'switch', 'access', 'complete', 'include']
                    if any(keyword in text.lower() for keyword in feature_keywords):
                        # Clean bullet markers
                        text = re.sub(r'^[•*\-]\s*', '', text)
                        if text not in data.features:
                            data.features.append(text)
        
        # Also check for structured feature divs with specific classes
        feature_divs = main_content.find_all(['div', 'p'], class_=re.compile(r'feature|benefit|capability', re.I))
        for div in feature_divs:
            text = div.get_text(strip=True)
            if len(text) > 20 and text not in data.features:
                data.features.append(text)
        
        # Extract included items - look for "Includes" section
        includes_heading = soup.find(['h2', 'h3', 'h4', 'h5'], string=lambda t: t and 'include' in t.lower() if t else False)
        if includes_heading:
            container = includes_heading.find_parent()
            if container:
                # Find list items or spans after the heading
                items = container.find_all(['li', 'span', 'div'])
                for item in items:
                    text = item.get_text(strip=True)
                    # Filter out quantity notes like "(1)" at start
                    text = re.sub(r'^\s*\(\d+\)\s*', '', text)
                    # Filter out common non-item text
                    if text and len(text) > 3 and text not in ['Includes', 'Included in the Box', 'Included']:
                        # Check if it looks like an item (not just descriptive text)
                        if not text.lower().startswith('see') and 'include' not in text.lower():
                            if text not in data.included_items:
                                data.included_items.append(text)
        
        # Extract description from "Product Overview" or similar sections
        overview_keywords = ['overview', 'description', 'about']
        for keyword in overview_keywords:
            overview = soup.find(string=re.compile(keyword, re.I))
            if overview:
                parent = overview.find_parent()
                if parent:
                    # Get text from this element and following siblings
                    desc_parts = []
                    # Get parent's text and next few siblings
                    for sibling in [parent] + list(parent.find_next_siblings(['p', 'div']))[:3]:
                        text = sibling.get_text(strip=True)
                        if len(text) > 20:
                            desc_parts.append(text)
                    if desc_parts:
                        data.description = ' '.join(desc_parts)
                        break
        
        # Extract main product image
        # Look for product images in various locations
        img_selectors = [
            ('img', {'src': lambda x: x and ('product' in x.lower() or data.sku.lower() in x.lower())}),
            ('img', {'class': lambda x: x and 'product' in str(x).lower()}),
        ]
        
        for tag, attrs in img_selectors:
            imgs = soup.find_all(tag, attrs=attrs)
            for img in imgs[:5]:
                image_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src') or img.get('data-original')
                if image_url:
                    if not image_url.startswith('http'):
                        image_url = 'https://www.dewalt.com' + image_url
                    data.image_url = image_url
                    break
            if data.image_url:
                break
        
        # Extract categories from breadcrumb navigation
        breadcrumb_selectors = [
            'nav[aria-label*="Breadcrumb"]',
            'nav.breadcrumb',
            'ol.breadcrumb',
            'nav',
        ]
        
        for selector in breadcrumb_selectors:
            breadcrumb = soup.select_one(selector)
            if breadcrumb:
                links = breadcrumb.find_all('a')
                for link in links:
                    text = link.get_text(strip=True)
                    # Filter out common non-category items
                    if text and text.lower() not in ['home', 'products', data.sku.lower()]:
                        if text not in data.categories:
                            data.categories.append(text)
                if data.categories:
                    break
        
        return data

