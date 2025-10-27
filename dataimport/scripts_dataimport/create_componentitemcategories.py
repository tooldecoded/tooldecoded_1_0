
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Components, ItemCategories
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ComponentItemCategory (2)')

for i in range(len(df)):
    component = Components.objects.get(sku=str(df.iloc[i]['component_sku']))
    itemcategory = ItemCategories.objects.get(name=str(df.iloc[i]['itemcategory_name']))
    component.itemcategories.add(itemcategory)
    component.save()
    print(f"Component {component.name} {itemcategory.name} added to Component {component.name}")
