
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Components, Statuses, BatteryPlatforms, BatteryVoltages, ProductLines, Statuses, MotorTypes
import pandas as pd

df = pd.read_excel('dataimport/ryobi full tools detail 2.xlsx', sheet_name='ComponentBatteryPlatform')

for i in range(len(df)):
    component = Components.objects.get(sku=str(df.iloc[i]['component_sku']))
    status = Statuses.objects.get(name='Active')
    batteryplatform = BatteryPlatforms.objects.get(name=str(df.iloc[i]['batteryplatform_name']))
    batteryvoltage = BatteryVoltages.objects.get(value=int(df.iloc[i]['voltage_value']))
    productline = ProductLines.objects.get(name=str(df.iloc[i]['productline_name']))
    motortype = MotorTypes.objects.get(name=str(df.iloc[i]['motortype_name']))
    
    #component.status = status
    component.batteryplatforms.add(batteryplatform)
    component.batteryvoltages.add(batteryvoltage)
    component.productlines.add(productline)
    component.motortype = motortype
    component.save()
    print(f"{batteryplatform.name} {batteryvoltage.value} {productline.name} {motortype.name} added to {component.name}")


