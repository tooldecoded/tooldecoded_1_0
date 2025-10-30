import os
import django
import sys
import google.generativeai as genai
import time
import json
import argparse
import decimal
from datetime import datetime

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

# Import your models
from toolanalysis.models import Components, ItemTypes

# Parse command line argumentsp
# Configure Gemini
genai.configure(api_key="AIzaSyCBU440DFi_w0L77QPpCKpO319nSU1hLBY")
model = genai.GenerativeModel("gemini-2.5-flash")


# Get a specific item type by name
item_type = ItemTypes.objects.get(name="Drill Drivers")

# Filter components by that item type
allcomponents = Components.objects.filter(itemtypes=item_type)

# Or filter products by that item type
components = Components.objects.filter(itemtypes=item_type)


for component in components:
    if component.standalone_price is None:
        print(f"{component.brand.name} {component.sku} {component.name} skipped")
    else:
        input_string = f"""# CRITICAL OUTPUT REQUIREMENTS
You MUST respond with ONLY with a numerical value with this component in the format #####0.00. Do not include any markdown formatting, explanations, or additional text outside the numerical value.

find the latest list price as of {datetime.now().strftime('%Y-%m-%d')} for this product from Home Depot, as a single bare tool or accessory, NOT A KIT.

# Example: 1099.99  

# CRITICAL REMINDERS
- Respond with ONLY the numerical value, no additional text. Use web search to find the latest list price, do not guess or make up a value.
the product model# is {component.brand.name} {component.sku} {component.name}
"""
        response = model.generate_content(input_string)
        if response.text:
            if decimal.Decimal(response.text) > 0:
                component.standalone_price = decimal.Decimal(response.text)
                component.save()
                print(f"{component.brand.name} {component.sku} {component.name}: {component.standalone_price}") 
            else:
                print(f"Invalid standalone price for {component.sku}: {response.text}")
        else:
            print(f"No response for {component.sku}")
        
        time.sleep(4)