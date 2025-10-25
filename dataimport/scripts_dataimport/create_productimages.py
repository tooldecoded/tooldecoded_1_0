
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ProductImages, Products
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ProductImage')

for i in range(len(df)):
    product = Products.objects.get(sku=str(df.iloc[i]['product_sku']))
    image = str(df.iloc[i]['productimage_image'])
    new_item, created = ProductImages.objects.update_or_create (
    product=product, image=image)
    if created:
        print(f"Product Image {product.name} {image} created")
    else:
        print(f"Product Image {product.name} {image} already exists")
