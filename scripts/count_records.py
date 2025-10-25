
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Attributes, Components, ProductComponents, ProductAccessories, ProductSpecifications, ProductImages, ProductStatusUpdates, ProductLines, Statuses
from toolanalysis.models import ComponentAttributes, BatteryPlatforms, BatteryVoltages, ListingTypes, Brands, Retailers
import pandas as pd

print(f"Attributes: {Attributes.objects.count()}")
print(f"Components: {Components.objects.count()}")
print(f"Product Components: {ProductComponents.objects.count()}")
print(f"Product Accessories: {ProductAccessories.objects.count()}")
print(f"Product Specifications: {ProductSpecifications.objects.count()}")
print(f"Product Images: {ProductImages.objects.count()}")
print(f"Product Status Updates: {ProductStatusUpdates.objects.count()}")
print(f"Product Lines: {ProductLines.objects.count()}")
print(f"Statuses: {Statuses.objects.count()}")
print(f"Component Attributes: {ComponentAttributes.objects.count()}")
print(f"Battery Platforms: {BatteryPlatforms.objects.count()}")
print(f"Battery Voltages: {BatteryVoltages.objects.count()}")
print(f"Listing Types: {ListingTypes.objects.count()}")
print(f"Brands: {Brands.objects.count()}")
print(f"Retailers: {Retailers.objects.count()}")


