
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Attributes
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='Attribute')

for i in range(len(df)):
    print(str(df.iloc[i]['attribute_name']) + " " + str(df.iloc[i]['attribute_unit']))
    name = str(df.iloc[i]['attribute_name'])
    unit = df.iloc[i]['attribute_unit']
    if pd.isna(unit):
        unit = None
        print("Attribute {name} has no unit")
    else:
        unit = str(unit)

    new_item, created = Attributes.objects.get_or_create (
    name=name, unit=unit)
    if created:
        print(f"Attribute {name} created")
    else:
        print(f"Attribute {name} already exists")


