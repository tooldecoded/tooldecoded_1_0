
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Components, BatteryVoltages
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ComponentVoltage')

for i in range(len(df)):
    component = Components.objects.get(sku=str(df.iloc[i]['component_sku']))
    voltage = BatteryVoltages.objects.get(value=int(df.iloc[i]['voltage_value']))
    print(f"Component {component.name} {voltage.value} added to Component {component.name}")
    component.batteryvoltages.add(voltage)
    component.save()

