
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Features
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='Feature')

for i in range(len(df)):
    name = str(df.iloc[i]['name'])
    description = df.iloc[i]['description']
    if pd.isna(description):
        description = None
    else:
        description = str(description)
    sortorder = df.iloc[i]['sortorder']
    if pd.isna(sortorder):
        sortorder = None
    else:
        sortorder = int(sortorder)
    existing_feature = Features.objects.get(name=name)
    if existing_feature is None:
        new_item, created = Features.objects.update_or_create (
        name=name, description=description, sortorder=sortorder)
        if created:
            print(f"Feature {name} created")
        else:
            print(f"Feature {name} already exists")
        new_item.description = description
        new_item.sortorder = sortorder
        new_item.save()
        print(f"Feature {name} updated")
    else:
        print(f"Feature {name} already exists")
        existing_feature.description = description
        existing_feature.sortorder = sortorder
        existing_feature.save()
        print(f"Feature {name} updated")        
  
