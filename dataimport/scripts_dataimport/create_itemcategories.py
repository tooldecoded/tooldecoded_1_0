
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ItemCategories
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ItemCategory (2)')

for i in range(len(df)):
    _name = str(df.iloc[i]['itemcategory_name'])
    _parent = str(df.iloc[i]['itemcategory_parent'])
    _level = int(df.iloc[i]['itemcategory_level'])
    _sortorder = (df.iloc[i]['itemcategory_sortOrder'])
    if pd.isna(_sortorder):
        print(f"Item Category {_name} has no sort order")
        _sortorder = None
    else:
        _sortorder = int(_sortorder)

    new_item, created = ItemCategories.objects.update_or_create (
    name=_name, level=_level, sortorder=_sortorder)

    if created:
        print(f"Item Category {_name} created")
        parent = ItemCategories.objects.get(name=_parent)
        new_item.parent = parent
        new_item.save()
        print(f"Item Category {_name} parent set to {parent.name}")
    else:
        print(f"Item Category {_name} already exists")

