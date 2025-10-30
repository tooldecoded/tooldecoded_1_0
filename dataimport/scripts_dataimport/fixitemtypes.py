import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ItemTypes

# Set to True to preview changes without saving
DRY_RUN = False

fixed_count = 0
for it in ItemTypes.objects.all().order_by('name'):
    fullname = (it.fullname or '').strip()
    if not fullname:
        continue

    parts = [p.strip() for p in fullname.split('/') if p.strip()]
    # Fix pattern: category/subcategory/category/itemtype → remove the second category
    if len(parts) >= 4 and parts[0] == parts[2]:
        new_fullname = '/'.join(parts[:2] + parts[3:])
        if new_fullname != fullname:
            print(f"{it.name}: '{fullname}' -> '{new_fullname}'")
            if not DRY_RUN:
                it.fullname = new_fullname
                it.save(update_fields=['fullname'])
            fixed_count += 1

print(f"Done. {'(dry run) ' if DRY_RUN else ''}Updated {fixed_count} item type(s).")