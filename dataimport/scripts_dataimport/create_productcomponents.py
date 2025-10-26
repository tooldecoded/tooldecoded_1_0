
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ProductComponents, Products, Components
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ProductComponent (3)')

for i in range(len(df)):
    product = Products.objects.get(sku=str(df.iloc[i]['product_sku']))
    component = Components.objects.get(sku=str(df.iloc[i]['component_sku']))
    new_item, created = ProductComponents.objects.update_or_create (
    product=product, component=component, quantity=str(df.iloc[i]['productcomponent_quantity']))
    if created:
        print(f"Product Component {product.name} {component.name} created")
    else:
        print(f"Product Component {product.name} {component.name} already exists")

