
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ProductSpecifications, Products
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ProductSpecification')

for i in range(len(df)):
    product = Products.objects.get(sku=str(df.iloc[i]['product_sku']))
    name = str(df.iloc[i]['productspecification_name'])
    value = str(df.iloc[i]['productspecification_value'])
    new_item, created = ProductSpecifications.objects.update_or_create (
    product=product, name=name, value=value)
    if created:
        print(f"Product Specification {product.name} {name} {value} created")
    else:
        print(f"Product Specification {product.name} {name} {value} already exists")
