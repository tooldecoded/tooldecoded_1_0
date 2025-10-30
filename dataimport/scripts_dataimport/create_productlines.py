
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ProductLines, BatteryPlatforms, BatteryVoltages, Brands
brand = Brands.objects.get(name='Ryobi')
batteryplatformoneplus = BatteryPlatforms.objects.get(name='18V ONE+')
v18 = BatteryVoltages.objects.get(value=18)
productlines = [['18V ONE+ HP', 'Ryobi 18V ONE+', brand , [batteryplatformoneplus], [v18]]]


for p in productlines:
    new_item, created = ProductLines.objects.update_or_create (
        name=p[0], brand=p[2])
    if created:
        print(f"Product Line {p[0]} created")
    else:
        print(f"Product Line {p[0]} already exists")
    new_item.batteryplatform.set(p[3])
    new_item.batteryvoltage.set(p[4])
    new_item.description = p[1]
    new_item.save()
    print(f"Product Line {p[0]} updated, {p[1]} added to Product Line {p[0]}, {p[2]} added to Product Line {p[0]}, {p[3]} added to Product Line {p[0]}, {p[4]} added to Product Line {p[0]}")


