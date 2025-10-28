
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Categories, Subcategories, ItemTypes, Components, Products, ItemCategories
import pandas as pd

for c in Components.objects.all():
    itemcategories = c.itemcategories.all()
    for ic in itemcategories:
        itemtype = ItemTypes.objects.get(name=ic.name)
        subcategory = Subcategories.objects.get(fullname=itemtype.subcategories.all()[0].fullname)
        category = Categories.objects.get(fullname=itemtype.categories.all()[0].fullname)
        c.itemtypes.add(itemtype)
        c.subcategories.add(subcategory)
        c.categories.add(category)
    c.save()
    print(f"Component {c.name} item types, subcategories, and categories updated")

for p in Products.objects.all():
    itemcategories = p.itemcategories.all()
    for ic in itemcategories:
        itemtype = ItemTypes.objects.get(name=ic.name)
        subcategory = Subcategories.objects.get(fullname=itemtype.subcategories.all()[0].fullname)
        category = Categories.objects.get(fullname=itemtype.categories.all()[0].fullname)
        p.itemtypes.add(itemtype)
        p.subcategories.add(subcategory)
        p.categories.add(category)
    p.save()
    print(f"Product {p.name} item types, subcategories, and categories updated")

print("Item types, subcategories, and categories migrated successfully")