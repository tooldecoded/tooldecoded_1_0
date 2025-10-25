
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import BatteryVoltages
voltages = [4,12,18,24,36,54]
for v in voltages:
    new_item, created = BatteryVoltages.objects.update_or_create (
    battery_voltage_value=v)
    if created:
        print(f"Battery Voltage {v} created")
    else:
        print(f"Battery Voltage {v} already exists")


