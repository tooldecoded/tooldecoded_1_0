
import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from toolanalysis.models import ItemCategories
import pandas as pd

df = pd.read_excel('dataimport/M18 Database.xlsx', sheet_name='ItemCategory')


parent = ItemCategories.objects.get(item_category_name='Power Tools')

childrennames=[
'Power Tool Combo Kits', 
'Batteries and Chargers',
'Drilling', 
'Fastening',
'Saws',
'Metalworking',
'Multi-Tools',
'Nailers, Staplers and Compressors',
'Sanders',
'Woodworking',
'Applicators',
'Concrete',
'Specialty Tools',
'Instruments',
'Electrical Installation',
'Plumbing Installation',
'Drain Cleaning',
'Portable Air Compressors'
]

for c in childrennames:
    child = ItemCategories.objects.get(item_category_name=c)
    child.item_category_parent = parent
    child.save()

    print(f"Item Category {c} parent set to {parent.item_category_name}")


parent = ItemCategories.objects.get(item_category_name='Outdoor Power Equipment')
childrennames=[
'Outdoor Power Equipment Combo Kits',
'Trimmers, Shears and Blowers', 
'Chain Saws and Pruning Saws',
'Mowers',
'Sprayers'
]

for c in childrennames:
    child = ItemCategories.objects.get(item_category_name=c)
    child.item_category_parent = parent
    child.save()

    print(f"Item Category {c} parent set to {parent.item_category_name}")

parent = ItemCategories.objects.get(item_category_name='Shop, Cleaning and Lifestyle')
childrennames=['Vacuums and Vacuum Accessories',
'Radios and Speakers',
'Power Generation',
'Heating and Cooling',
'Combo Kits',
'Crafting',
'Cleaning',
'Lighting', 
'Shop Blowers',
'Storage'
]

for c in childrennames:
    child = ItemCategories.objects.get(item_category_name=c)
    child.item_category_parent = parent
    child.save()

    print(f"Item Category {c} parent set to {parent.item_category_name}")

parentchildren =[['Chain Saws and Pruning Saws','Chain Saws'],
['Chain Saws and Pruning Saws','Pruning Saws'],
['Chain Saws and Pruning Saws','Pole Saws'],
['Outdoor Power Equipment Combo Kits','All Outdoor Power Equipment Combo Kits'],
['Mowers','Lawn Mowers'],
['Sprayers','Sprayer Accessories'],
['Sprayers','Chemical Sprayers'],
['Trimmers, Shears and Blowers','Attachments'],
['Trimmers, Shears and Blowers','Leaf Blowers'],
['Trimmers, Shears and Blowers','Brush Cutters'],
['Trimmers, Shears and Blowers','Edgers'],
['Trimmers, Shears and Blowers','Hedge Trimmers'],
['Trimmers, Shears and Blowers','Pruning Shears'],
['Trimmers, Shears and Blowers','String Trimmers'],
['Trimmers, Shears and Blowers','Trimmer Accessories'],
['Applicators','Caulk Guns'],
['Applicators','Grease Guns'],
['Batteries and Chargers','Batteries'],
['Batteries and Chargers','Chargers'],
['Power Tool Combo Kits','All Power Tool Combo Kits'],
['Concrete','Concrete Vibrators'],
['Concrete','Concrete Cutting'],
['Concrete','Rotary Hammers'],
['Drain Cleaning','Drain Cleaning Accessories'],
['Drain Cleaning','Drum Machines'],
['Drain Cleaning','Sectional Machines'],
['Drain Cleaning','Sink Machines'],
['Drilling','Drill Drivers'],
['Drilling','Hammer Drills'],
['Drilling','Magnetic Drills'],
['Drilling','Right Angle Drills'],
['Electrical Installation','Cable Strippers'],
['Electrical Installation','Conduit Benders'],
['Electrical Installation','Crimpers'],
['Electrical Installation','Cutters'],
['Electrical Installation','Electrical Cutting Tools'],
['Electrical Installation','Fish Tapes'],
['Electrical Installation','Knockout'],
['Electrical Installation','Pumps'],
['Electrical Installation','Threading'],
['Fastening','Impact Drivers'],
['Fastening','Impact Wrenches'],
['Fastening','Ratchets'],
['Fastening','Screwdrivers'],
['Instruments','Inspection Equipment'],
['Instruments','Lasers'],
['Metalworking','Band Saw Accessories'],
['Metalworking','Band Saws'],
['Metalworking','Cutting'],
['Metalworking','Grinders'],
['Metalworking','Metal Cutting'],
['Metalworking','Sander and Polisher Accessories'],
['Metalworking','Sanders and Polishers'],
['Metalworking','Shears and Nibblers'],
['Multi-Tools','Multi-Tool Accessories'],
['Multi-Tools','Oscillating Multi-Tools'],
['Nailers, Staplers and Compressors','Compressors'],
['Nailers, Staplers and Compressors','Brad Nailers'],
['Nailers, Staplers and Compressors','Finish Nailers'],
['Nailers, Staplers and Compressors','Framing Nailers'],
['Nailers, Staplers and Compressors','Roofing Nailers'],
['Nailers, Staplers and Compressors','Staplers'],
['Plumbing Installation','Expansion Tools'],
['Plumbing Installation','Press Tools'],
['Plumbing Installation','Transfer Pumps'],
['Sanders','Belt Sanders'],
['Sanders','Random Orbit Sanders'],
['Sanders','Sheet Sanders'],
['Saws','Circular Saw Blades'],
['Saws','Circular Saws'],
['Saws','Jig Saws'],
['Saws','Miter Saws'],
['Saws','Plunge Cut Saws'],
['Saws','Reciprocating Saws'],
['Saws','Table Saws'],
['Specialty Tools','Mixers'],
['Specialty Tools','Rivet Tools'],
['Woodworking','Planers'],
['Woodworking','Routers'],
['Cleaning','Compact Blowers'],
['Crafting','Heating Tools'],
['Heating and Cooling','Fans'],
['Heating and Cooling','Heaters'],
['Lighting','Flood Lights'],
['Lighting','Handheld Lights'],
['Lighting','Lighting Accessories'],
['Lighting','Site Lights'],
['Lighting','Specialty Lights'],
['Lighting','Task Lighting'],
['Lighting','Tower Lights'],
['Power Generation','Power Supplies'],
['Radios and Speakers','Radios'],
['Radios and Speakers','Speakers'],
['Storage','Tool Boxes and Bags'],
['Storage','Modular Storage Systems'],
['Vacuums and Vacuum Accessories','Compact Vacuums'],
['Vacuums and Vacuum Accessories','Vacuum Accessories'],
['Vacuums and Vacuum Accessories','Wet Dry Vacuums'],
]

for p,c in parentchildren:
    parent = ItemCategories.objects.get(item_category_name=p)
    child = ItemCategories.objects.get(item_category_name=c)
    child.item_category_parent = parent
    child.save()

    print(f"Item Category {c} parent set to {parent.item_category_name}")
