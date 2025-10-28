
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Components
set_true_skus =[
    '2904-20',
    '2903-20',
    '2905-20',
    '2906-20',
    'PBLDD02',
    'PBLHM102',
    'DCD1007B'
]

for sku in set_true_skus:
    print(sku)
    component = Components.objects.get(sku=sku)
    component.is_featured = True
    component.save()
    print(f"Component {component.name} is featured")

