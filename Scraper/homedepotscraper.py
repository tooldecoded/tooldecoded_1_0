import requests
from bs4 import BeautifulSoup
import time
import json
import csv
from urllib.parse import urljoin
import re
from difflib import SequenceMatcher

class HomeDepotScraper:
    def __init__(self):
        self.base_url = "https://www.homedepot.com"
        self.session = requests.Session()
        
        # Basic headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
    
    def search_products(self, search_term, max_pages=1, min_match_score=0.3):
        """Search for products with URL-based matching"""
        products = []
        
        for page in range(1, max_pages + 1):
            search_url = f"{self.base_url}/s/{search_term}"
            if page > 1:
                search_url += f"?Nao={24 * (page - 1)}"
            
            print(f"Scraping page {page} for '{search_term}'...")
            
            try:
                response = self.session.get(search_url)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                page_products = self._extract_from_structured_data(soup, search_term, min_match_score)
                products.extend(page_products)
                
                time.sleep(2)
                
            except Exception as e:
                print(f"Error on page {page}: {e}")
                continue
        
        return products
    
    def _extract_from_structured_data(self, soup, search_term, min_match_score):
        """Extract products from JSON-LD structured data with URL-based matching"""
        products = []
        
        # Find the script tag with structured data
        script_tag = soup.find('script', {'id': 'thd-helmet__script--browseSearchStructuredData'})
        
        if not script_tag:
            print("No structured data found")
            return products
        
        try:
            # Parse the JSON data
            json_data = json.loads(script_tag.string)
            
            # Navigate to the products
            if json_data and len(json_data) > 0:
                main_entity = json_data[0].get('mainEntity', {})
                offers = main_entity.get('offers', {})
                products_data = offers.get('itemOffered', [])
                
                for product_data in products_data:
                    # Check if product matches search term using URL slug
                    match_score = self._calculate_url_match_score(product_data, search_term)
                    
                    if match_score >= min_match_score:
                        product = {
                            'name': product_data.get('name', ''),
                            'brand': product_data.get('brand', {}).get('name', ''),
                            'description': product_data.get('description', ''),
                            'sku': product_data.get('sku', ''),
                            'image': product_data.get('image', ''),
                            'url': product_data.get('offers', {}).get('url', ''),
                            'price': product_data.get('offers', {}).get('price', ''),
                            'currency': product_data.get('offers', {}).get('priceCurrency', ''),
                            'availability': product_data.get('offers', {}).get('availability', ''),
                            'rating': product_data.get('aggregateRating', {}).get('ratingValue', ''),
                            'review_count': product_data.get('aggregateRating', {}).get('reviewCount', ''),
                            'match_score': match_score,
                            'url_slug': self._extract_url_slug(product_data.get('offers', {}).get('url', ''))
                        }
                        products.append(product)
                        print(f"✓ Match found: {product['name'][:50]}... (score: {match_score:.2f})")
                    else:
                        print(f"✗ No match: {product_data.get('name', '')[:50]}... (score: {match_score:.2f})")
                    
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
        except Exception as e:
            print(f"Error extracting structured data: {e}")
        
        return products
    
    def _extract_url_slug(self, url):
        """Extract the slug part from Home Depot URL"""
        if not url:
            return ""
        
        # Pattern: /p/{slug}/{sku}
        match = re.search(r'/p/([^/]+)/', url)
        if match:
            return match.group(1)
        return ""
    
    def _calculate_url_match_score(self, product_data, search_term):
        """Calculate match score based on URL slug structure"""
        url = product_data.get('offers', {}).get('url', '')
        slug = self._extract_url_slug(url)
        
        if not slug:
            return 0.0
        
        search_lower = search_term.lower().strip()
        slug_lower = slug.lower()
        
        # Check for exact matches in slug
        if search_lower in slug_lower:
            return 1.0
        
        # Check for partial matches
        search_words = search_lower.split()
        matches = 0
        
        for word in search_words:
            if word in slug_lower:
                matches += 1
        
        if len(search_words) > 0:
            return matches / len(search_words)
        
        return 0.0
    
    def search_by_sku(self, sku):
        """Search by SKU - most reliable method"""
        return self.search_products(sku, min_match_score=0.8)
    
    def search_by_model(self, model):
        """Search by model number using URL slug matching"""
        return self.search_products(model, min_match_score=0.7)
    
    def search_by_brand_and_model(self, brand, model):
        """Search by brand and model"""
        search_term = f"{brand} {model}"
        return self.search_products(search_term, min_match_score=0.6)
    
    def search_by_brand_and_sku(self, brand, sku):
        """Search by brand and SKU for exact matching"""
        search_term = f"{brand} {sku}"
        return self.search_products(search_term, min_match_score=0.8)
    
    def search_exact_sku(self, sku):
        """Search for exact SKU match"""
        return self.search_products(sku, min_match_score=0.9)
    
    def get_product_by_sku(self, sku):
        """Get a specific product by SKU"""
        # Try direct SKU search first
        products = self.search_by_sku(sku)
        
        if products:
            return products[0]
        
        # If not found, try searching for the model number
        # Extract model from SKU if possible
        model_match = re.search(r'(\d{4}-\d{2})', sku)
        if model_match:
            model = model_match.group(1)
            products = self.search_by_model(model)
            return products[0] if products else None
        
        return None

def main():
    scraper = HomeDepotScraper()
    
    # Test URL-based matching
    print("=== Testing URL Slug Matching ===")
    products = scraper.search_by_model("2903-20")
    
    for product in products:
        print(f"Product: {product['name']}")
        print(f"URL Slug: {product['url_slug']}")
        print(f"SKU: {product['sku']}")
        print(f"Match Score: {product['match_score']:.2f}")
        print(f"URL: {product['url']}")
        print()

if __name__ == "__main__":
    main()