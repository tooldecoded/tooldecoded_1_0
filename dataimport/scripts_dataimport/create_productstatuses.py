
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Products, Statuses
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='Product')

for i in range(len(df)):
    product = Products.objects.get(sku=str(df.iloc[i]['product_sku']))
    status = Statuses.objects.get(name=str(df.iloc[i]['product_status']))
   
    
    product.status = status
    product.save()
    print(f"Product {product.name} {status.name} added to Product {product.name}")


