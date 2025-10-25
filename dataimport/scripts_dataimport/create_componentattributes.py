
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ComponentAttributes, Components, Attributes
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ComponentAttribute')

for i in range(len(df)):
    component = Components.objects.get(sku=str(df.iloc[i]['component_sku']))
    attribute = Attributes.objects.get(name=str(df.iloc[i]['attribute_name']))
    value = str(df.iloc[i]['componentattribute_value'])
    new_item, created = ComponentAttributes.objects.update_or_create (
    component=component, attribute=attribute, value=value)
    if created:
        print(f"Component Attribute {component.name} {attribute.name} {value} created")
    else:
        print(f"Component Attribute {component.name} {attribute.name} {value} already exists")
