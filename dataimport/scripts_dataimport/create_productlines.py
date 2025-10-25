
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ProductLines, BatteryPlatforms, BatteryVoltages, Brands
brand = Brands.objects.get(name='Milwaukee')
batterym12 = BatteryPlatforms.objects.get(name='M12')
batterym18 = BatteryPlatforms.objects.get(name='M18')
v12 = BatteryVoltages.objects.get(value=12)
v18 = BatteryVoltages.objects.get(value=18)
productlines = [['M18', 'Milwaukee M18', brand , [batterym18], [v18]],
['M12', 'Milwaukee M12', brand , [batterym12], [v12]],
['M18 FUEL', 'Milwaukee M18 FUEL', brand , [batterym18], [v18]],
['M12 FUEL', 'Milwaukee M12 FUEL', brand , [batterym12], [v12]],
['M18 Brushless', 'Milwaukee M18 Brushless', brand , [batterym18], [v18]],
['M18 Compact Brushless', 'Milwaukee M18 Compact Brushless', brand , [batterym18], [v18]],
['M12 Compact Brushless', 'Milwaukee M12 Compact Brushless', brand , [batterym12], [v12]],
['M12 Subcompact Brushless', 'Milwaukee M12 Subcompact Brushless', brand , [batterym12], [v12]],
['M18 REDLITHIUM HIGH OUTPUT', 'Milwaukee M18 REDLITHIUM HIGH OUTPUT', brand , [batterym18], [v18]],
['M18 REDLITHIUM FORGE', 'Milwaukee M18 REDLITHIUM FORGE', brand , [batterym18], [v18]],
['M18 REDLITHIUM CP', 'Milwaukee M18 REDLITHIUM CP', brand , [batterym18], [v18]],
['M18 REDLITHIUM XC', 'Milwaukee M18 REDLITHIUM XC', brand , [batterym18], [v18]],
['M18 REDLITHIUM HIGH DEMAND', 'Milwaukee M18 REDLITHIUM HIGH DEMAND', brand , [batterym18], [v18]]]


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


