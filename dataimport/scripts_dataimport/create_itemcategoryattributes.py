
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ItemCategories, Attributes
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ItemCategoryAttribute')

for i in range(len(df)):
    itemcategory = ItemCategories.objects.get(name=str(df.iloc[i]['itemcategory_name']))
    attribute = Attributes.objects.get(name=str(df.iloc[i]['attribute_name']))
    itemcategory.attributes.add(attribute)  
    itemcategory.save()
    print(f"Item Category {itemcategory.name} {attribute.name} added to Item Category {itemcategory.name}")
