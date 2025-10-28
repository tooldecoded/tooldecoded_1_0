
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Products, BatteryVoltages, BatteryPlatforms, ProductLines
import pandas as pd

df = pd.read_excel('dataimport/ryobi full tools detail 2.xlsx', sheet_name='ProductBatteryPlatform')

for i in range(len(df)):
    product = Products.objects.get(sku=str(df.iloc[i]['product_sku']))
    voltage = BatteryVoltages.objects.get(value=int(df.iloc[i]['voltage_value']))
    batteryplatform = BatteryPlatforms.objects.get(name=str(df.iloc[i]['batteryplatform_name']))
    product.batteryplatforms.add(batteryplatform)
    product.batteryvoltages.add(voltage)
    product.save()
    print(f"Product {product.name} {voltage.value} added to Product {product.name}, {batteryplatform.name} added to Product {product.name}")
