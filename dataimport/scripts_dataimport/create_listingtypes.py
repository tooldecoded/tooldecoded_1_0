
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ListingTypes
listingtypes = ['Manufacturer', 'Manufacturer Implied', 'Retailer']
for l in listingtypes:
    new_item, created = ListingTypes.objects.update_or_create (
    listing_type_name=l)
    if created:
        print(f"Listing Type {l} created")
    else:
        print(f"Listing Type {l} already exists")


