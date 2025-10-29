import os
import django
import sys
from datetime import datetime, timedelta

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import PriceListings, Retailers

def get_unmatched_listings(days=7, retailer_name='Home Depot'):
    """Get unmatched price listings from the last N days"""
    
    # Calculate date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get retailer
    try:
        retailer = Retailers.objects.get(name=retailer_name)
    except Retailers.DoesNotExist:
        print(f"Retailer '{retailer_name}' not found")
        return
    
    # Query unmatched listings
    unmatched = PriceListings.objects.filter(
        retailer=retailer,
        product__isnull=True,
        datepulled__gte=start_date
    ).order_by('-datepulled', 'retailer_sku')
    
    print(f"Unmatched {retailer_name} listings from {start_date} to {end_date}")
    print("=" * 60)
    print(f"Found {unmatched.count()} unmatched listings")
    print()
    
    for listing in unmatched:
        print(f"SKU: {listing.retailer_sku}")
        print(f"Price: ${listing.price}")
        print(f"URL: {listing.url}")
        print(f"Date: {listing.datepulled}")
        print("-" * 40)
    
    return unmatched

def get_unmatched_summary():
    """Get summary of unmatched listings by retailer"""
    
    print("Unmatched Listings Summary")
    print("=" * 40)
    
    retailers = Retailers.objects.all()
    
    for retailer in retailers:
        unmatched_count = PriceListings.objects.filter(
            retailer=retailer,
            product__isnull=True
        ).count()
        
        total_count = PriceListings.objects.filter(
            retailer=retailer
        ).count()
        
        if total_count > 0:
            unmatched_rate = (unmatched_count / total_count) * 100
            print(f"{retailer.name}: {unmatched_count}/{total_count} ({unmatched_rate:.1f}%)")
        else:
            print(f"{retailer.name}: No listings found")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Query unmatched price listings')
    parser.add_argument('--days', type=int, default=7, help='Number of days to look back')
    parser.add_argument('--retailer', default='Home Depot', help='Retailer name to filter by')
    parser.add_argument('--summary', action='store_true', help='Show summary instead of detailed list')
    
    args = parser.parse_args()
    
    if args.summary:
        get_unmatched_summary()
    else:
        get_unmatched_listings(days=args.days, retailer_name=args.retailer)

if __name__ == "__main__":
    main()
