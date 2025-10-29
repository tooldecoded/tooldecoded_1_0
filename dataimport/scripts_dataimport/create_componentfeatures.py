
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ComponentFeatures, Components, Features
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ComponentFeature')

'''for i in range(len(df)):
    component = Components.objects.get(sku=str(df.iloc[i]['component_sku']))
    feature = Features.objects.get(name=str(df.iloc[i]['feature_name']))
    value = str(df.iloc[i]['feature_value'])
    new_item, created = ComponentFeatures.objects.update_or_create (
    component=component, feature=feature, value=value)
    if created:
        print(f"Component Feature {component.name} {feature.name} {value} created")
    else:
        print(f"Component Feature {component.name} {feature.name} {value} already exists")

for i in range(len(df)):
    component = Components.objects.get(sku=str(df.iloc[i]['component_sku']))
    feature = Features.objects.get(name=str(df.iloc[i]['feature_name']))
    value = (df.iloc[i]['feature_value'])
    if pd.isna(value):
        value = None
    else:
        value = str(value)
    componentfeature = ComponentFeatures.objects.get(component=component, feature=feature)
    print(componentfeature.value)
    if componentfeature is None:
        print(f"Component Feature {component.name} {feature.name} {value} not found")
    componentfeature.value = value
    componentfeature.save()
    print(f"Component Feature {component.name} {feature.name} {value} updated")
'''

for i in range(len(df)):
    component = Components.objects.get(sku=str(df.iloc[i]['component_sku']))
    feature = Features.objects.get(name=str(df.iloc[i]['feature_name']))
    component.features.add(feature)
    component.save()
    print(f"Component {component.name} {feature.name} added to Component {component.name}")