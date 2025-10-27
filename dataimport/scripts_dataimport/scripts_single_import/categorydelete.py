
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Components, ItemCategories, Products

oldcategory = ItemCategories.objects.get(name='Plunge Cut Saws')
newcategory = ItemCategories.objects.get(name='Miter Saws')
component = Components.objects.get(sku='PGC21')
product = Products.objects.get(sku='PGC21K')

component.itemcategories.remove(oldcategory)
component.itemcategories.add(newcategory)
product.itemcategories.remove(oldcategory)
product.itemcategories.add(newcategory)

print(f"Component {component.name} category updated to {newcategory.name}")
print(f"Product {product.name} category updated to {newcategory.name}")

