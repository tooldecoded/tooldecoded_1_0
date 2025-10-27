
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Components, ItemCategories, Brands, ListingTypes
import pandas as pd

df = pd.read_excel('dataimport/ryobi full tools detail 2.xlsx', sheet_name='Component')

for i in range(len(df)):

    component = Components.objects.get(sku=str(df.iloc[i]['component_sku']))
    image = df.iloc[i]['component_image']
    if pd.isna(image):
        image = None
    else:
        image = str(image)

    if image != component.image:
        component.image = image
        component.save() # update the image if it changed
        print(f"Component {component.name} image updated")
    else:
        print(f"Component {component.name} image unchanged")


