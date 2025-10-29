import os
import django
import sys
import time
from datetime import datetime
from decimal import Decimal

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Products, Retailers, PriceListings
from homedepotscraper import HomeDepotScraper

class HomeDepotPriceScraper:
    def __init__(self, delay=2, limit=None):
        self.scraper = HomeDepotScraper()
        self.delay = delay
        self.limit = limit
        self.home_depot_retailer = None
        self.stats = {
            'total_processed': 0,
            'matched': 0,
            'unmatched': 0,
            'errors': 0,
            'no_results': 0
        }
        self.not_found_products = []
        self.error_products = []
    
    def get_home_depot_retailer(self):
        """Get or create Home Depot retailer record"""
        if not self.home_depot_retailer:
            self.home_depot_retailer, created = Retailers.objects.get_or_create(
                name='Home Depot',
                defaults={'url': 'https://www.homedepot.com'}
            )
            if created:
                print(f"Created Home Depot retailer record")
            else:
                print(f"Using existing Home Depot retailer record")
        return self.home_depot_retailer
    
    def match_product(self, hd_product, db_product):
        """Match Home Depot product to database product"""
        # Check brand match
        hd_brand = hd_product.get('brand', '').lower().strip()
        db_brand = db_product.brand.name.lower().strip() if db_product.brand else ''
        
        if hd_brand != db_brand:
            return False, 0.0
        
        # Check SKU match
        hd_sku = hd_product.get('sku', '').lower().strip()
        db_sku = db_product.sku.lower().strip() if db_product.sku else ''
        
        if hd_sku == db_sku:
            return True, 1.0
        
        # Check if DB SKU is in HD SKU or URL slug
        hd_url_slug = hd_product.get('url_slug', '').lower()
        if db_sku in hd_sku or db_sku in hd_url_slug:
            return True, 0.9
        
        # Check if HD SKU is in DB SKU
        if hd_sku in db_sku:
            return True, 0.8
        
        return False, 0.0
    
    def save_price_listing(self, retailer, product, hd_data):
        """Save matched price listing"""
        try:
            price_listing, created = PriceListings.objects.update_or_create(
                retailer=retailer,
                product=product,
                defaults={
                    'price': Decimal(str(hd_data['price'])),
                    'currency': 'USD',
                    'url': hd_data['url'],
                    'datepulled': datetime.now().date()
                }
            )
            
            if created:
                print(f"  ✓ Created price listing: ${hd_data['price']}")
            else:
                print(f"  ✓ Updated price listing: ${hd_data['price']}")
            
            return True
        except Exception as e:
            print(f"  ✗ Error saving price listing: {e}")
            return False
    
    def save_unmatched_listing(self, retailer, hd_data):
        """Save unmatched price listing with retailer SKU only"""
        try:
            price_listing, created = PriceListings.objects.update_or_create(
                retailer=retailer,
                product=None,
                retailer_sku=hd_data['sku'],
                defaults={
                    'price': Decimal(str(hd_data['price'])),
                    'currency': 'USD',
                    'url': hd_data['url'],
                    'datepulled': datetime.now().date()
                }
            )
            
            if created:
                print(f"  ✓ Created unmatched listing: {hd_data['sku']} - ${hd_data['price']}")
            else:
                print(f"  ✓ Updated unmatched listing: {hd_data['sku']} - ${hd_data['price']}")
            
            return True
        except Exception as e:
            print(f"  ✗ Error saving unmatched listing: {e}")
            return False
    
    def scrape_product(self, product):
        """Scrape prices for a single product"""
        print(f"\nProcessing: {product.brand.name if product.brand else 'No Brand'} - {product.sku}")
        
        if not product.sku:
            print("  ✗ No SKU, skipping")
            return False
        
        # Search Home Depot
        search_term = f"{product.brand.name} {product.sku}" if product.brand else product.sku
        hd_products = self.scraper.search_products(search_term, max_pages=1, min_match_score=0.3)
        
        if not hd_products:
            print("  ✗ No Home Depot results found")
            self.stats['no_results'] += 1
            self.not_found_products.append({
                'brand': product.brand.name if product.brand else 'No Brand',
                'sku': product.sku,
                'name': product.name,
                'search_term': search_term
            })
            return False
        
        retailer = self.get_home_depot_retailer()
        matched = False
        
        for hd_product in hd_products:
            is_match, score = self.match_product(hd_product, product)
            
            if is_match and score >= 0.8:
                print(f"  ✓ Match found (score: {score:.2f}): {hd_product['name'][:50]}...")
                if self.save_price_listing(retailer, product, hd_product):
                    self.stats['matched'] += 1
                    matched = True
                break
            elif is_match and score >= 0.5:
                print(f"  ? Partial match (score: {score:.2f}): {hd_product['name'][:50]}...")
                # Save as unmatched for manual review
                if self.save_unmatched_listing(retailer, hd_product):
                    self.stats['unmatched'] += 1
                    matched = True
        
        if not matched:
            print("  ✗ No good matches found")
            # Save the first result as unmatched for manual review
            if hd_products:
                if self.save_unmatched_listing(retailer, hd_products[0]):
                    self.stats['unmatched'] += 1
        
        return True
    
    def scrape_all_products(self):
        """Scrape prices for all products with SKUs"""
        print("Starting Home Depot price scraping...")
        print("=" * 50)
        
        # Get all products with SKUs
        products = Products.objects.filter(sku__isnull=False).exclude(sku='')
        
        if self.limit:
            products = products[:self.limit]
            print(f"Limited to {self.limit} products for testing")
        
        total_products = products.count()
        print(f"Found {total_products} products with SKUs")
        
        for i, product in enumerate(products, 1):
            print(f"\n[{i}/{total_products}] ", end="")
            
            try:
                self.scrape_product(product)
                self.stats['total_processed'] += 1
                
                # Delay between requests
                if i < total_products:
                    time.sleep(self.delay)
                    
            except Exception as e:
                print(f"  ✗ Error processing product: {e}")
                self.stats['errors'] += 1
                self.error_products.append({
                    'brand': product.brand.name if product.brand else 'No Brand',
                    'sku': product.sku,
                    'name': product.name,
                    'error': str(e)
                })
                continue
        
        self.print_summary()
    
    def print_summary(self):
        """Print scraping summary"""
        print("\n" + "=" * 50)
        print("SCRAPING SUMMARY")
        print("=" * 50)
        print(f"Total processed: {self.stats['total_processed']}")
        print(f"Matched products: {self.stats['matched']}")
        print(f"Unmatched products: {self.stats['unmatched']}")
        print(f"No results found: {self.stats['no_results']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.stats['total_processed'] > 0:
            match_rate = (self.stats['matched'] / self.stats['total_processed']) * 100
            print(f"Match rate: {match_rate:.1f}%")
        
        # Show products not found
        if self.not_found_products:
            print(f"\nPRODUCTS NOT FOUND ON HOME DEPOT ({len(self.not_found_products)}):")
            print("-" * 50)
            for product in self.not_found_products:
                print(f"• {product['brand']} - {product['sku']} ({product['name'][:50]}...)")
                print(f"  Search term: {product['search_term']}")
        
        # Show products with errors
        if self.error_products:
            print(f"\nPRODUCTS WITH ERRORS ({len(self.error_products)}):")
            print("-" * 50)
            for product in self.error_products:
                print(f"• {product['brand']} - {product['sku']} ({product['name'][:50]}...)")
                print(f"  Error: {product['error']}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape Home Depot prices')
    parser.add_argument('--limit', type=int, help='Limit number of products to process')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests in seconds')
    
    args = parser.parse_args()
    
    scraper = HomeDepotPriceScraper(delay=args.delay, limit=args.limit)
    scraper.scrape_all_products()

if __name__ == "__main__":
    main()
