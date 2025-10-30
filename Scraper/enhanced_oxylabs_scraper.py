import requests
import json
import csv
import time
import re
from datetime import datetime
from pprint import pprint
from bs4 import BeautifulSoup
import logging
from urllib.parse import urljoin

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedOxylabsScraper:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = "https://realtime.oxylabs.io/v1/queries"
        self.session = requests.Session()
        
    def scrape_with_retry(self, url, max_retries=3, delay=2):
        """Scrape a URL with retry logic and error handling"""
        payload = {
            'source': 'universal',
            'url': url,
        }
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{max_retries} for URL: {url}")
                
                response = self.session.request(
                    'POST',
                    self.base_url,
                    auth=(self.username, self.password),
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info("Scraping successful!")
                    return response.json()
                else:
                    logger.warning(f"Attempt {attempt + 1} failed with status {response.status_code}")
                    if response.status_code == 401:
                        logger.error("Authentication failed - check credentials")
                        return None
                        
            except requests.exceptions.RequestException as e:
                logger.error(f"Attempt {attempt + 1} failed with error: {e}")
                
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
        
        logger.error("All attempts failed")
        return None
    
    def extract_products_from_home_depot(self, response_data):
        """Extract products using the proven Home Depot selectors from hdtest.py"""
        if not response_data or 'results' not in response_data:
            return []
        
        html_content = response_data['results'][0]['content']
        soup = BeautifulSoup(html_content, 'html.parser')
        
        products = []
        
        # Use the proven selectors from hdtest.py
        product_elements = soup.find_all('div', {'data-testid': 'product-pod'})
        
        if not product_elements:
            logger.warning("No product-pod elements found")
            return []
        
        logger.info(f"Found {len(product_elements)} product pods")
        
        for i, product in enumerate(product_elements):
            try:
                product_data = self._extract_single_home_depot_product(product)
                if product_data:
                    products.append(product_data)
            except Exception as e:
                logger.warning(f"Error extracting product {i}: {e}")
                continue
        
        logger.info(f"Successfully extracted {len(products)} products")
        return products
    
    def _extract_single_home_depot_product(self, product_element):
        """Extract data from a single Home Depot product using proven selectors"""
        product_data = {}
        
        # Product ID - ALWAYS WORKS (from hdtest.py)
        product_data['product_id'] = product_element.get('data-product-id', 'N/A')
        
        # Brand - ALWAYS WORKS (from hdtest.py)
        brand_elem = product_element.find('span', {'data-testid': 'attribute-brandname-inline'})
        product_data['brand'] = brand_elem.get_text().strip() if brand_elem else 'N/A'
        
        # Product Name - ALWAYS WORKS (from hdtest.py)
        name_elem = product_element.find('span', {'data-testid': 'attribute-product-label'})
        product_data['name'] = name_elem.get_text().strip() if name_elem else 'N/A'
        
        # Price - ALWAYS WORKS (from hdtest.py)
        price_elem = product_element.find('span', class_='sui-text-3xl')
        product_data['price'] = price_elem.get_text().strip() if price_elem else 'N/A'
        
        # Model Number - ALWAYS WORKS (from hdtest.py)
        model_text = product_element.get_text()
        model_match = re.search(r'Model#\s*([A-Z0-9-]+)', model_text)
        product_data['model'] = model_match.group(1) if model_match else 'N/A'
        
        # Rating - ALWAYS WORKS (from hdtest.py)
        rating_match = re.search(r'\((\d+\.\d+)\s*/\s*(\d+)\)', model_text)
        product_data['rating'] = f"{rating_match.group(1)}/5 ({rating_match.group(2)} reviews)" if rating_match else 'N/A'
        
        # Product Link - ALWAYS WORKS (from hdtest.py)
        link_elem = product_element.find('a', href=True)
        product_data['url'] = f"https://www.homedepot.com{link_elem['href']}" if link_elem else 'N/A'
        
        # Stock Limit - ALWAYS WORKS (from hdtest.py)
        stock_match = re.search(r'Limit (\d+) per order', model_text)
        product_data['stock_limit'] = stock_match.group(1) if stock_match else 'N/A'
        
        # Extract SKU from URL if available
        if product_data['url'] != 'N/A':
            sku_match = re.search(r'/(\d+)$', product_data['url'])
            product_data['sku'] = sku_match.group(1) if sku_match else 'N/A'
        else:
            product_data['sku'] = 'N/A'
        
        # Extract image
        img_elem = product_element.find('img', src=True)
        product_data['image'] = img_elem['src'] if img_elem else 'N/A'
        
        # Extract description if available
        desc_elem = product_element.find('div', class_=lambda x: x and 'description' in x.lower())
        product_data['description'] = desc_elem.get_text().strip() if desc_elem else 'N/A'
        
        return product_data
    
    def extract_structured_data_products(self, response_data):
        """Extract products from JSON-LD structured data (from homedepotscraper.py)"""
        if not response_data or 'results' not in response_data:
            return []
        
        html_content = response_data['results'][0]['content']
        soup = BeautifulSoup(html_content, 'html.parser')
        
        products = []
        
        # Find the script tag with structured data (from homedepotscraper.py)
        script_tag = soup.find('script', {'id': 'thd-helmet__script--browseSearchStructuredData'})
        
        if not script_tag:
            logger.warning("No structured data found")
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
                        'url_slug': self._extract_url_slug(product_data.get('offers', {}).get('url', ''))
                    }
                    products.append(product)
                    
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {e}")
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
        
        return products
    
    def _extract_url_slug(self, url):
        """Extract the slug part from Home Depot URL (from homedepotscraper.py)"""
        if not url:
            return ""
        
        # Pattern: /p/{slug}/{sku}
        match = re.search(r'/p/([^/]+)/', url)
        if match:
            return match.group(1)
        return ""
    
    def save_results(self, products, format='json', filename_prefix='homedepot_products'):
        """Save products to file in specified format"""
        if not products:
            logger.warning("No products to save")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == 'json':
            filename = f"{filename_prefix}_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {filename}")
            return filename
        
        elif format == 'csv':
            filename = f"{filename_prefix}_{timestamp}.csv"
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if products:
                    writer = csv.DictWriter(f, fieldnames=products[0].keys())
                    writer.writeheader()
                    writer.writerows(products)
            logger.info(f"Results saved to {filename}")
            return filename
        
        return None
    
    def scrape_home_depot_category(self, url, use_structured_data=False, save_format='both'):
        """Scrape a Home Depot category page"""
        logger.info(f"Starting scrape for: {url}")
        
        result = self.scrape_with_retry(url)
        if not result:
            return None
        
        # Try both extraction methods
        products = []
        
        if use_structured_data:
            structured_products = self.extract_structured_data_products(result)
            products.extend(structured_products)
            logger.info(f"Found {len(structured_products)} products from structured data")
        
        # Always try the proven HTML extraction method
        html_products = self.extract_products_from_home_depot(result)
        products.extend(html_products)
        logger.info(f"Found {len(html_products)} products from HTML extraction")
        
        # Remove duplicates based on SKU
        unique_products = []
        seen_skus = set()
        
        for product in products:
            sku = product.get('sku', '')
            if sku and sku not in seen_skus:
                unique_products.append(product)
                seen_skus.add(sku)
            elif not sku:  # Include products without SKU
                unique_products.append(product)
        
        logger.info(f"Total unique products: {len(unique_products)}")
        
        if unique_products:
            if save_format in ['json', 'both']:
                self.save_results(unique_products, 'json')
            if save_format in ['csv', 'both']:
                self.save_results(unique_products, 'csv')
        
        return unique_products
    
    def scrape_multiple_categories(self, urls, delay_between_requests=5, use_structured_data=False):
        """Scrape multiple Home Depot categories with rate limiting"""
        all_products = []
        
        for i, url in enumerate(urls, 1):
            logger.info(f"Scraping URL {i}/{len(urls)}: {url}")
            
            products = self.scrape_home_depot_category(url, use_structured_data=use_structured_data, save_format='none')
            
            if products:
                all_products.extend(products)
                logger.info(f"Found {len(products)} products (Total: {len(all_products)})")
            else:
                logger.warning("Failed to scrape this URL")
            
            # Add delay between requests to be respectful
            if i < len(urls):
                logger.info(f"Waiting {delay_between_requests} seconds before next request...")
                time.sleep(delay_between_requests)
        
        # Save all products together
        if all_products:
            self.save_results(all_products, 'json', 'homedepot_all_products')
            self.save_results(all_products, 'csv', 'homedepot_all_products')
        
        return all_products

# Main execution
if __name__ == "__main__":
    # Set your Oxylabs API Credentials
    username = "tooldecoded_c7GJz"  # Using the correct username from your file
    password = "5gM_3jpR=afdFAb"
    
    # Initialize scraper
    scraper = EnhancedOxylabsScraper(username, password)
    
    # Test URL from your existing scripts
    test_url = 'https://www.homedepot.com/b/Tools-Power-Tools-Drills-Hammer-Drills/Milwaukee/Milwaukee-M18/N-5yc1vZc8wtZzvZ1z17rdr'
    
    print("=== Enhanced Home Depot Scraper with Oxylabs ===")
    print(f"Scraping: {test_url}")
    print()
    
    # Test both extraction methods
    products = scraper.scrape_home_depot_category(test_url, use_structured_data=True)
    
    if products:
        print(f"\n=== RESULTS ===")
        print(f"Found {len(products)} products:")
        print()
        
        for i, product in enumerate(products[:10], 1):  # Show first 10
            print(f"{i}. {product.get('name', 'No title')}")
            print(f"   Brand: {product.get('brand', 'No brand')}")
            print(f"   Price: {product.get('price', 'No price')}")
            print(f"   SKU: {product.get('sku', 'No SKU')}")
            print(f"   Model: {product.get('model', 'No model')}")
            print(f"   Rating: {product.get('rating', 'No rating')}")
            print(f"   Link: {product.get('url', 'No link')}")
            print()
        
        if len(products) > 10:
            print(f"... and {len(products) - 10} more products")
    else:
        print("No products found or scraping failed")
