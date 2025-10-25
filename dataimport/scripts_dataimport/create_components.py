
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Components, ItemCategories, Brands, ListingTypes
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='Component')

for i in range(len(df)):
    name = str(df.iloc[i]['component_name'])
    brand = Brands.objects.get(name='Milwaukee')
    sku = str(df.iloc[i]['component_sku'])
    image = str(df.iloc[i]['component_image'])


    new_item, created = Components.objects.update_or_create (
    name=name, brand=brand, sku=sku, image=image)
    if created:
        print(f"Component {name} created")
    else:
        print(f"Component {name} already exists")


