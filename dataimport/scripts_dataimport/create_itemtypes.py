
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ItemTypes, Categories, Subcategories
import pandas as pd


x = 2


if x == 1:
    new_item, created = Subcategories.objects.update_or_create (
    name='Apparel', fullname='Shop, Cleaning and Lifestyle/Apparel', 
    sortorder=11)
    if created:
        new_item.categories.add(Categories.objects.get(name='Shop, Cleaning and Lifestyle'))
        new_item.save()
        print(f"Subcategory {new_item.name} created")
    else:
        new_item.categories.add(Categories.objects.get(name='Shop, Cleaning and Lifestyle'))
        new_item.save()
        print(f"Subcategory {new_item.name} updated")


if x == 2:
    new_item, created = ItemTypes.objects.update_or_create (
    name='Palm Nailers', fullname='Power Tools/Nailers, Staplers and Compressors/Palm Nailers', 
    sortorder=11)
    if created:
        new_item.categories.add(Categories.objects.get(name='Power Tools'))
        new_item.subcategories.add(Subcategories.objects.get(name='Nailers, Staplers and Compressors'))
        new_item.save()
        print(f"Item Type {new_item.name} created")
    else:
        new_item.categories.add(Categories.objects.get(name='Power Tools'))
        new_item.subcategories.add(Subcategories.objects.get(name='Nailers, Staplers and Compressors'))
        new_item.save()
        print(f"Item Type {new_item.name} updated")
