import os
import django
import sys
import csv
from datetime import datetime, timedelta

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Products, PriceListings, Retailers

def export_not_found_products(days=7, retailer_name='Home Depot', output_file=None):
    """Export products that were not found on Home Depot to CSV"""
    
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"not_found_products_{timestamp}.csv"
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get all products with SKUs
    products_with_skus = Products.objects.filter(sku__isnull=False).exclude(sku='')
    
    # Get products that have been searched (have price listings)
    searched_products = PriceListings.objects.filter(
        datepulled__gte=start_date
    ).values_list('product_id', flat=True).distinct()
    
    # Get products that were NOT found (no price listings)
    not_found_products = products_with_skus.exclude(id__in=searched_products)
    
    print(f"Found {not_found_products.count()} products not searched in the last {days} days")
    print(f"Exporting to: {output_file}")
    
    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['brand', 'sku', 'name', 'description', 'categories', 'subcategories']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for product in not_found_products:
            # Get categories and subcategories
            categories = ', '.join([cat.name for cat in product.categories.all()])
            subcategories = ', '.join([sub.name for sub in product.subcategories.all()])
            
            writer.writerow({
                'brand': product.brand.name if product.brand else 'No Brand',
                'sku': product.sku,
                'name': product.name,
                'description': product.description or '',
                'categories': categories,
                'subcategories': subcategories
            })
    
    print(f"Exported {not_found_products.count()} products to {output_file}")
    return output_file

def export_products_with_errors(days=7, output_file=None):
    """Export products that had errors during scraping"""
    
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"error_products_{timestamp}.csv"
    
    # This would need to be implemented by storing error logs
    # For now, just show the concept
    print("Error export not yet implemented - would need error logging")
    return None

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Export products not found on Home Depot')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back')
    parser.add_argument('--output', help='Output CSV file name')
    parser.add_argument('--retailer', default='Home Depot', help='Retailer name')
    
    args = parser.parse_args()
    
    export_not_found_products(
        days=args.days, 
        retailer_name=args.retailer,
        output_file=args.output
    )

if __name__ == "__main__":
    main()
