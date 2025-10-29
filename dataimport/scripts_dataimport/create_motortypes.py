
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import MotorTypes
motortypes = ['Brushless', 'Brushed', 'Mixed']
for m in motortypes:
    new_item, created = MotorTypes.objects.update_or_create (
    name=m)
    if created:
        print(f"Motor Type {m} created")
    else:
        print(f"Motor Type {m} already exists")

