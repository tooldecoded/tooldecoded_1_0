
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ProductAccessories, Products
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ProductAccessory (3)')

for i in range(len(df)):
    product = Products.objects.get(sku=str(df.iloc[i]['product_sku']))
    name = str(df.iloc[i]['productaccessory_name'])
    quantity = int(df.iloc[i]['productaccessory_quantity'])
    new_item, created = ProductAccessories.objects.update_or_create (
    product=product, name=name, quantity=quantity)
    if created:
        print(f"Product Accessory {product.name} {name} {quantity} created")
    else:
        print(f"Product Accessory {product.name} {name} {quantity} already exists")
