
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Components, Features, Products

hammerdrills = Products.objects.filter(itemtypes__name='Hammer Drills')
hammerfeature = Features.objects.get(name='Hammer Mode')
for hammerdrill in hammerdrills:
    hammerdrill.features.add(hammerfeature)
    hammerdrill.save()
    print(f"{hammerfeature.name} added to Component {hammerdrill.name}")