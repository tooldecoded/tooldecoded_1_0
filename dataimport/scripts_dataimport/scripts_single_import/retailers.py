
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Retailers

retailers = [['Home Depot','https://www.homedepot.com']]


for r in retailers:
    new_item, created = Retailers.objects.update_or_create (
    name=r[0], url=r[1])
    if created:
        print(f"Retailer {r[0]} created")
    else:
        print(f"Retailer {r[0]} already exists")


