
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Components, MotorTypes, ComponentAttributes, Attributes
import pandas as pd

components = Components.objects.filter(itemtypes__name='Vacuum Accessories')

for component in components:
    if component.motortype:
        existingmotortype = component.motortype
        component.motortype = None
        component.save()
        print(f"Motor Type {existingmotortype.name} deleted for {component.name}")
    else:
        print(f"Motor Type not exists for {component.name}")
