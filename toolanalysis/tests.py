
import os
import django

from django.test import TestCase
from toolanalysis.models import Attribute

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import Attribute

new_item = Attribute(attribute_name="Length", attribute_uom="in")
# Create your tests here.
new_item.save()

print(new_item.id)
