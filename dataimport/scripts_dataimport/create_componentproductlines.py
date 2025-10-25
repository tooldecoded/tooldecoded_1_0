
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Components, ProductLines
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ComponentProductLine')

for i in range(len(df)):
    print(f"Component {df.iloc[i]['component_sku']} {df.iloc[i]['productline_name']}")
    component = Components.objects.get(sku=str(df.iloc[i]['component_sku']))
    productline = ProductLines.objects.get(name=str(df.iloc[i]['productline_name']))
    component.productlines.add(productline)
    component.save()

