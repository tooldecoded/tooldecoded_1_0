
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ItemTypes, Attributes
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ItemTypeAttribute')

for i in range(len(df)):
    itemtype = ItemTypes.objects.get(name=str(df.iloc[i]['itemtype_name']))
    attribute = Attributes.objects.get(name=str(df.iloc[i]['attribute_name']))
    itemtype.attributes.add(attribute)  
    itemtype.save()
    print(f"{attribute.name} added to Item Type {itemtype.name}")
