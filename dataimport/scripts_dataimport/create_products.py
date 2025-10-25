
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Products, ItemCategories, Brands, ListingTypes
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='Product')

for i in range(len(df)):
    name = str(df.iloc[i]['product_name'])
    description = str(df.iloc[i]['product_description'])
    if pd.isna(description):
        description = ''
    brand = Brands.objects.get(name='Milwaukee')
    sku = str(df.iloc[i]['product_sku'])
    image = str(df.iloc[i]['product_image'])
    listingtype = ListingTypes.objects.get(name=str(df.iloc[i]['product_listingtype']))
    bullets = str(df.iloc[i]['product_bullets'])


    new_item, created = Products.objects.update_or_create (
    name=name, description=description, brand=brand, sku=sku, image=image, listingtype=listingtype, bullets=bullets)
    if created:
        print(f"Product {name} created")
    else:
        print(f"Product {name} already exists")


