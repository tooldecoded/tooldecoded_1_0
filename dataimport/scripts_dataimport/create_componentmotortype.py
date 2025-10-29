
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Products, MotorTypes
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ComponentMotorType')

for i in range(len(df)):
    product = Products.objects.get(sku=str(df.iloc[i]['component_sku']))
    motorType = MotorTypes.objects.get(name=str(df.iloc[i]['motor_type_name']))
    product.motortype = motorType
    product.save()
    print(f"{motorType.name} added to Product {product.name}")

