"""Generic manufacturer product page parser using Gemini."""

import re
import time
from typing import Dict, List

import requests

from .base import ManufacturerParser, ParsedProductData
from .gemini_html_parser import GeminiHTMLParser


class GenericManufacturerParser(ManufacturerParser):
    """Generic parser for any manufacturer product pages using Gemini."""
    
    def __init__(self, brand: str):
        """
        Initialize parser with brand name.
        
        Args:
            brand: Manufacturer brand name (e.g., "DEWALT", "Milwaukee")
        """
        self.brand = brand
        self.gemini_parser = GeminiHTMLParser()
    
    def detect_manufacturer(self, url: str) -> str:
        """Return the brand name this parser is configured for."""
        return self.brand if self.validate_url(url) else ""
    
    def validate_url(self, url: str) -> bool:
        """Check if URL appears to be a valid product page."""
        # Generic validation - just check if it's an HTTP(S) URL
        return url.startswith(('http://', 'https://')) and len(url) > 10
    
    def parse(self, url: str) -> ParsedProductData:
        """Parse product page from URL."""
        data = ParsedProductData(source_url=url, brand=self.brand)
        
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
        response = None
        
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
        
        if not response:
            # This should not happen, but handle it just in case
            data.add_error(f"Failed to fetch URL after {max_retries} attempts: {str(last_exception)}")
            return data
        
        # Parse the fetched HTML using Gemini
        return self.parse_from_html(response.text, source_url=url)
    
    def parse_from_html(self, html: str, source_url: str = "") -> ParsedProductData:
        """Parse product page from HTML source code using Gemini File API."""
        # Use Gemini HTML parser with the configured brand
        data = self.gemini_parser.parse_html(html, brand=self.brand, source_url=source_url)
        return data

