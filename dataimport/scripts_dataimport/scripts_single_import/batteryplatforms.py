
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import BatteryPlatforms, BatteryVoltages, Brands
brand = Brands.objects.get(name='Dewalt')
v18 = BatteryVoltages.objects.get(value=18)

batteryplatforms = [['20V MAX*',brand , [v18]]]


for b in batteryplatforms:
    new_item, created = BatteryPlatforms.objects.update_or_create (
    name=b[0], brand=b[1])
    if created:
        new_item.voltage.set(b[2])
        print(f"Battery Platform {b[0]} created, {b[2]} added to Battery Platform {b[0]}")
    else:
        print(f"Battery Platform {b[0]} already exists")


