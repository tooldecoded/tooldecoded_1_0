
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
print(sys.path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Statuses
statuses = [['Active',1],['Discontinued',2],['Pre-Release',3]]
for s in statuses:
    new_item, created = Statuses.objects.update_or_create (
    name=s[0])
    if created:
        print(f"Status {s} created")
    else:
        print(f"Status {s} already exists")
        new_item.sortorder = s[1]
        new_item.save()
        print(f"Status {s} updated")


