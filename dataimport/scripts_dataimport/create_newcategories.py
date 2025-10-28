
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Categories, Subcategories, ItemTypes
import pandas as pd

df = pd.read_excel('dataimport/ryobi full tools detail 2.xlsx', sheet_name='ItemType')

for i in range(len(df)):
    name = str(df.iloc[i]['name'])
    fullname = str(df.iloc[i]['fullname'])
    if pd.isna(df.iloc[i]['sortorder']):
        sortorder = None
    else:
        sortorder = int(df.iloc[i]['sortorder'])

    new_item, created = ItemTypes.objects.update_or_create (
    name=name, fullname=fullname, sortorder=sortorder)

    if created:
        print(f"Item Type {name} created")
    else:
        print(f"Item Type {name} already exists")

    itemtype = ItemTypes.objects.get(fullname=str(df.iloc[i]['fullname']))
    subcategory = Subcategories.objects.get(fullname=str(df.iloc[i]['subcategoryfullname']))
    category = Categories.objects.get(fullname=str(df.iloc[i]['categoryfullname']))
    itemtype.subcategories.add(subcategory)
    itemtype.categories.add(category)
    itemtype.save()

    print(f"Item Type {itemtype.fullname} added to Subcategory {subcategory.fullname} and Category {category.fullname}")

    