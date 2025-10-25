
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Brands
brands = [['Milwaukee', '#C92A28', '', 1],
['Dewalt', '#FEBD16', '', 2],
['Ryobi', '#C9CF17', '', 3],
['Makita', '#008397', '', 4],
['Ridgid', '#000000', '', 5],
['Bosch', '#013B69', '', 6],
['Metabo HPT', '#11A277', '', 7],
['SKIL', '#E52415', '', 8],
['Kobalt', '#274586', '', 9],
['Craftsman', '#DD0424', '', 10]]

for b in brands:
    new_item, created = Brands.objects.update_or_create (
    brand_name=b[0], brand_color=b[1], brand_logo=b[2], brand_sortorder=b[3])
    if created:
        print(f"Brand {b[0]} created")
    else:
        print(f"Brand {b[0]} already exists")


