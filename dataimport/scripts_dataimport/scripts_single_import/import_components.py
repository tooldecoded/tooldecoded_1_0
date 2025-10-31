import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()
from pathlib import Path
from toolanalysis.models import Components, ItemTypes, Subcategories, Categories, Brands, ListingTypes, BatteryPlatforms, BatteryVoltages, ProductLines, MotorTypes, Features
import pandas as pd
from tkinter import filedialog, messagebox
import tkinter as tk

# Open file picker dialog
root = tk.Tk()
root.withdraw()  # Hide the main window

file_path = filedialog.askopenfilename(
    title="Select Excel file",
    filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
)

# Check if user cancelled
if not file_path:
    print("No file selected. Exiting...")
    sys.exit(0)

file_path = Path(file_path)

# Validate file exists (should always be true from dialog, but just in case)
if not file_path.exists():
    print(f"Error: File not found: {file_path}")
    sys.exit(1)

print(f"Reading Excel file: {file_path}")

# Open Excel file and get sheet names
try:
    excel_file = pd.ExcelFile(file_path)
    sheet_names = excel_file.sheet_names
    
    # Create dialog for sheet selection
    selected_sheet = None
    
    def on_select():
        selection = listbox.curselection()
        if selection:
            dialog.selected_sheet = sheet_names[selection[0]]
            dialog.destroy()
        else:
            messagebox.showwarning("No Selection", "Please select a sheet first.")
    
    def on_double_click(event):
        selection = listbox.curselection()
        if selection:
            on_select()
    
    dialog = tk.Toplevel(root)
    dialog.title("Select Sheet/Tab")
    dialog.geometry("400x300")
    dialog.selected_sheet = None  # Initialize before creating widgets
    
    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
    y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    
    # Make sure dialog stays on top
    dialog.lift()
    dialog.attributes('-topmost', True)
    dialog.after_idle(lambda: dialog.attributes('-topmost', False))
    
    # Label
    label = tk.Label(dialog, text="Select a sheet to import:", font=("Arial", 10))
    label.pack(pady=10)
    
    # Listbox with scrollbar
    frame = tk.Frame(dialog)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 10))
    scrollbar.config(command=listbox.yview)
    
    for sheet_name in sheet_names:
        listbox.insert(tk.END, sheet_name)
    
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    listbox.bind('<Double-Button-1>', on_double_click)
    if sheet_names:  # Only if there are sheets
        listbox.selection_set(0)  # Select first item by default
    
    # Buttons
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=10)
    
    ok_button = tk.Button(button_frame, text="OK", command=on_select, width=10)
    ok_button.pack(side=tk.LEFT, padx=5)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=lambda: (setattr(dialog, 'selected_sheet', None), dialog.destroy()), width=10)
    cancel_button.pack(side=tk.LEFT, padx=5)
    
    dialog.transient(root)
    dialog.grab_set()
    dialog.focus_set()
    
    # Wait for dialog to close
    root.deiconify()  # Make sure root is available (even if hidden)
    dialog.wait_window()
    
    selected_sheet = dialog.selected_sheet
    
    if not selected_sheet:
        print("No sheet selected. Exiting...")
        sys.exit(0)
    
    print(f"\nReading sheet: {selected_sheet}")
    df = pd.read_excel(file_path, sheet_name=selected_sheet)
    print(f"Loaded {len(df)} rows and {len(df.columns)} columns")
    
except Exception as e:
    print(f"Error reading Excel file: {str(e)}")
    sys.exit(1)

# Clean up root window
root.destroy()

# Helper function to safely get column value
def get_col(row, col_name):
    """Get column value if column exists and is not NaN, otherwise return None"""
    if col_name in df.columns:
        value = row[col_name]
        return value if pd.notna(value) else None
    return None

for i in range(len(df)):
    row = df.iloc[i]
    
    if 'action' not in df.columns:
        print(f"Row {i+1}: Skipping - 'action' column not found")
        continue
    
    action = get_col(row, 'action')
    if action:
        sku = get_col(row, 'sku')
        brand = get_col(row, 'brand')
        name = get_col(row, 'name')
        description = get_col(row, 'description')
        image = get_col(row, 'image')
        listingtype = get_col(row, 'listingtype')
        itemtype = get_col(row, 'itemtypefullname')
        subcategory = get_col(row, 'subcategoryfullname')
        category = get_col(row, 'categoryfullname')
        batteryplatform = get_col(row, 'batteryplatform')
        batteryvoltage = get_col(row, 'batteryvoltage')
        motortype = get_col(row, 'motortype')
        features = get_col(row, 'features')
        productline = get_col(row, 'productline')
        is_featured = get_col(row, 'is_featured')
        isaccessory = get_col(row, 'isaccessory')
        standalone_price = get_col(row, 'standalone_price')
        showcase_priority = get_col(row, 'showcase_priority')
        
        if action == 'delete':
            if sku and brand:
                try:
                    brand_obj = Brands.objects.get(name=brand)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    component.delete()
                    print(f"Component {component.name} deleted")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand}' not found")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component not found")
        elif action == 'update':
            if sku and brand:
                try:
                    brand_obj = Brands.objects.get(name=brand)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    
                    # Simple fields
                    if name is not None:
                        component.name = name
                    if description is not None:
                        component.description = description
                    if brand:
                        try:
                            component.brand = brand_obj  # Use the already-fetched object
                        except Brands.DoesNotExist:
                            print(f"Row {i+1}: Brand '{brand}' not found, skipping")
                    if sku:
                        component.sku = sku
                    if image is not None:
                        component.image = image
                    if listingtype:
                        try:
                            component.listingtype = ListingTypes.objects.get(name=listingtype)
                        except ListingTypes.DoesNotExist:
                            print(f"Row {i+1}: ListingType '{listingtype}' not found, skipping")
                    if motortype:
                        try:
                            component.motortype = MotorTypes.objects.get(name=motortype)
                        except MotorTypes.DoesNotExist:
                            print(f"Row {i+1}: MotorType '{motortype}' not found, skipping")
                    if is_featured is not None:
                        component.is_featured = bool(is_featured)
                    if standalone_price is not None:
                        try:
                            component.standalone_price = float(standalone_price)
                        except (ValueError, TypeError):
                            print(f"Row {i+1}: Invalid standalone_price '{standalone_price}', skipping")
                    if showcase_priority is not None:
                        try:
                            component.showcase_priority = int(showcase_priority)
                        except (ValueError, TypeError):
                            print(f"Row {i+1}: Invalid showcase_priority '{showcase_priority}', skipping")
                    if isaccessory is not None:
                        component.isaccessory = bool(isaccessory)
                    
                    # ManyToMany fields (add without clearing to preserve existing relationships)
                    if itemtype:
                        try:
                            component.itemtypes.add(ItemTypes.objects.get(fullname=itemtype))
                        except ItemTypes.DoesNotExist:
                            print(f"Row {i+1}: ItemType '{itemtype}' not found, skipping")
                    if subcategory:
                        try:
                            component.subcategories.add(Subcategories.objects.get(fullname=subcategory))
                        except Subcategories.DoesNotExist:
                            print(f"Row {i+1}: Subcategory '{subcategory}' not found, skipping")
                    if category:
                        try:
                            component.categories.add(Categories.objects.get(fullname=category))
                        except Categories.DoesNotExist:
                            print(f"Row {i+1}: Category '{category}' not found, skipping")
                    if batteryplatform:
                        try:
                            component.batteryplatforms.add(BatteryPlatforms.objects.get(name=batteryplatform))
                        except BatteryPlatforms.DoesNotExist:
                            print(f"Row {i+1}: BatteryPlatform '{batteryplatform}' not found, skipping")
                    if batteryvoltage:
                        try:
                            component.batteryvoltages.add(BatteryVoltages.objects.get(name=batteryvoltage))
                        except BatteryVoltages.DoesNotExist:
                            print(f"Row {i+1}: BatteryVoltage '{batteryvoltage}' not found, skipping")
                    if productline:
                        try:
                            component.productlines.add(ProductLines.objects.get(name=productline))
                        except ProductLines.DoesNotExist:
                            print(f"Row {i+1}: ProductLine '{productline}' not found, skipping")
                    if features:
                        # Handle comma-separated features if needed
                        feature_names = [f.strip() for f in str(features).split(',')]
                        for feat_name in feature_names:
                            try:
                                component.features.add(Features.objects.get(name=feat_name))
                            except Features.DoesNotExist:
                                print(f"Row {i+1}: Feature '{feat_name}' not found")
                    
                    component.save()
                    print(f"Component {component.name} updated")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component not found for update")
        elif action == 'purge':
            # Purge: Clear only fields that are present in the Excel headers (excluding action, brand, sku)
            if sku and brand:
                try:
                    brand_obj = Brands.objects.get(name=brand)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    
                    # Get list of columns to purge (exclude action, brand, sku which are needed for identification)
                    columns_to_purge = [col for col in df.columns if col.lower() not in ['action', 'brand', 'sku']]
                    purged_fields = []
                    
                    for col_name in columns_to_purge:
                        try:
                            # Map column names to component fields
                            if col_name == 'name':
                                component.name = ''
                                purged_fields.append('name')
                            elif col_name == 'description':
                                component.description = None
                                purged_fields.append('description')
                            elif col_name == 'image':
                                component.image = None
                                purged_fields.append('image')
                            elif col_name == 'listingtype':
                                component.listingtype = None
                                purged_fields.append('listingtype')
                            elif col_name == 'motortype':
                                component.motortype = None
                                purged_fields.append('motortype')
                            elif col_name == 'is_featured':
                                component.is_featured = False
                                purged_fields.append('is_featured')
                            elif col_name == 'isaccessory':
                                component.isaccessory = False
                                purged_fields.append('isaccessory')
                            elif col_name == 'standalone_price':
                                component.standalone_price = None
                                purged_fields.append('standalone_price')
                            elif col_name == 'showcase_priority':
                                component.showcase_priority = 0
                                purged_fields.append('showcase_priority')
                            elif col_name == 'itemtypefullname' or col_name == 'itemtype':
                                component.itemtypes.clear()
                                purged_fields.append('itemtypes')
                            elif col_name == 'subcategoryfullname' or col_name == 'subcategory':
                                component.subcategories.clear()
                                purged_fields.append('subcategories')
                            elif col_name == 'categoryfullname' or col_name == 'category':
                                component.categories.clear()
                                purged_fields.append('categories')
                            elif col_name == 'batteryplatform':
                                component.batteryplatforms.clear()
                                purged_fields.append('batteryplatforms')
                            elif col_name == 'batteryvoltage':
                                component.batteryvoltages.clear()
                                purged_fields.append('batteryvoltages')
                            elif col_name == 'productline':
                                component.productlines.clear()
                                purged_fields.append('productlines')
                            elif col_name == 'features':
                                component.features.clear()
                                purged_fields.append('features')
                        except Exception as e:
                            print(f"Row {i+1}: Error purging field '{col_name}': {str(e)}")
                    
                    component.save()
                    if purged_fields:
                        print(f"Component {component.name} purged: Cleared fields: {', '.join(purged_fields)}")
                    else:
                        print(f"Component {component.name}: No fields to purge (no matching columns found in sheet)")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand}' not found")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component with SKU '{sku}' and brand '{brand}' not found")
            else:
                print(f"Row {i+1}: Skipping purge - missing required fields (sku or brand)")
        elif action == 'create':
            # Check if component already exists
            if sku and brand:
                try:
                    brand_obj = Brands.objects.get(name=brand)
                    try:
                        # Component exists, update it instead
                        component = Components.objects.get(sku=sku, brand=brand_obj)
                        
                        # Simple fields
                        if name is not None:
                            component.name = name
                        if description is not None:
                            component.description = description
                        if brand:
                            try:
                                component.brand = brand_obj  # Use the already-fetched object
                            except Brands.DoesNotExist:
                                print(f"Row {i+1}: Brand '{brand}' not found, skipping")
                        if sku:
                            component.sku = sku
                        if image is not None:
                            component.image = image
                        if listingtype:
                            try:
                                component.listingtype = ListingTypes.objects.get(name=listingtype)
                            except ListingTypes.DoesNotExist:
                                print(f"Row {i+1}: ListingType '{listingtype}' not found, skipping")
                        if motortype:
                            try:
                                component.motortype = MotorTypes.objects.get(name=motortype)
                            except MotorTypes.DoesNotExist:
                                print(f"Row {i+1}: MotorType '{motortype}' not found, skipping")
                        if is_featured is not None:
                            component.is_featured = bool(is_featured)
                        if standalone_price is not None:
                            try:
                                component.standalone_price = float(standalone_price)
                            except (ValueError, TypeError):
                                print(f"Row {i+1}: Invalid standalone_price '{standalone_price}', skipping")
                        if showcase_priority is not None:
                            try:
                                component.showcase_priority = int(showcase_priority)
                            except (ValueError, TypeError):
                                print(f"Row {i+1}: Invalid showcase_priority '{showcase_priority}', skipping")
                        if isaccessory is not None:
                            component.isaccessory = bool(isaccessory)
                        
                        # ManyToMany fields (add without clearing to preserve existing relationships)
                        if itemtype:
                            try:
                                component.itemtypes.add(ItemTypes.objects.get(fullname=itemtype))
                            except ItemTypes.DoesNotExist:
                                print(f"Row {i+1}: ItemType '{itemtype}' not found, skipping")
                        if subcategory:
                            try:
                                component.subcategories.add(Subcategories.objects.get(fullname=subcategory))
                            except Subcategories.DoesNotExist:
                                print(f"Row {i+1}: Subcategory '{subcategory}' not found, skipping")
                        if category:
                            try:
                                component.categories.add(Categories.objects.get(fullname=category))
                            except Categories.DoesNotExist:
                                print(f"Row {i+1}: Category '{category}' not found, skipping")
                        if batteryplatform:
                            try:
                                component.batteryplatforms.add(BatteryPlatforms.objects.get(name=batteryplatform))
                            except BatteryPlatforms.DoesNotExist:
                                print(f"Row {i+1}: BatteryPlatform '{batteryplatform}' not found, skipping")
                        if batteryvoltage:
                            try:
                                component.batteryvoltages.add(BatteryVoltages.objects.get(name=batteryvoltage))
                            except BatteryVoltages.DoesNotExist:
                                print(f"Row {i+1}: BatteryVoltage '{batteryvoltage}' not found, skipping")
                        if productline:
                            try:
                                component.productlines.add(ProductLines.objects.get(name=productline))
                            except ProductLines.DoesNotExist:
                                print(f"Row {i+1}: ProductLine '{productline}' not found, skipping")
                        if features:
                            feature_names = [f.strip() for f in str(features).split(',')]
                            for feat_name in feature_names:
                                try:
                                    component.features.add(Features.objects.get(name=feat_name))
                                except Features.DoesNotExist:
                                    print(f"Row {i+1}: Feature '{feat_name}' not found")
                        
                        component.save()
                        print(f"Component {component.name} updated (was create action, but component already existed)")
                        
                    except Components.DoesNotExist:
                        # Component doesn't exist, create it
                        create_data = {}
                        if name is not None:
                            create_data['name'] = name
                        if description is not None:
                            create_data['description'] = description
                        if brand:
                            try:
                                create_data['brand'] = Brands.objects.get(name=brand)
                            except Brands.DoesNotExist:
                                print(f"Row {i+1}: Brand '{brand}' not found, skipping brand")
                        if sku:
                            create_data['sku'] = sku
                        if image is not None:
                            create_data['image'] = image
                        if listingtype:
                            try:
                                create_data['listingtype'] = ListingTypes.objects.get(name=listingtype)
                            except ListingTypes.DoesNotExist:
                                print(f"Row {i+1}: ListingType '{listingtype}' not found, skipping")
                        if motortype:
                            try:
                                create_data['motortype'] = MotorTypes.objects.get(name=motortype)
                            except MotorTypes.DoesNotExist:
                                print(f"Row {i+1}: MotorType '{motortype}' not found, skipping")
                        if is_featured is not None:
                            create_data['is_featured'] = bool(is_featured)
                        if standalone_price is not None:
                            try:
                                create_data['standalone_price'] = float(standalone_price)
                            except (ValueError, TypeError):
                                print(f"Row {i+1}: Invalid standalone_price '{standalone_price}', skipping")
                        if showcase_priority is not None:
                            try:
                                create_data['showcase_priority'] = int(showcase_priority)
                            except (ValueError, TypeError):
                                print(f"Row {i+1}: Invalid showcase_priority '{showcase_priority}', skipping")
                        if isaccessory is not None:
                            create_data['isaccessory'] = bool(isaccessory)
                        
                        if 'name' in create_data:
                            component = Components.objects.create(**create_data)
                            
                            # Set ManyToMany fields after creation
                            if itemtype:
                                try:
                                    component.itemtypes.add(ItemTypes.objects.get(fullname=itemtype))
                                except ItemTypes.DoesNotExist:
                                    print(f"Row {i+1}: ItemType '{itemtype}' not found, skipping")
                            if subcategory:
                                try:
                                    component.subcategories.add(Subcategories.objects.get(fullname=subcategory))
                                except Subcategories.DoesNotExist:
                                    print(f"Row {i+1}: Subcategory '{subcategory}' not found, skipping")
                            if category:
                                try:
                                    component.categories.add(Categories.objects.get(fullname=category))
                                except Categories.DoesNotExist:
                                    print(f"Row {i+1}: Category '{category}' not found, skipping")
                            if batteryplatform:
                                try:
                                    component.batteryplatforms.add(BatteryPlatforms.objects.get(name=batteryplatform))
                                except BatteryPlatforms.DoesNotExist:
                                    print(f"Row {i+1}: BatteryPlatform '{batteryplatform}' not found, skipping")
                            if batteryvoltage:
                                try:
                                    component.batteryvoltages.add(BatteryVoltages.objects.get(name=batteryvoltage))
                                except BatteryVoltages.DoesNotExist:
                                    print(f"Row {i+1}: BatteryVoltage '{batteryvoltage}' not found, skipping")
                            if productline:
                                try:
                                    component.productlines.add(ProductLines.objects.get(name=productline))
                                except ProductLines.DoesNotExist:
                                    print(f"Row {i+1}: ProductLine '{productline}' not found, skipping")
                            if features:
                                feature_names = [f.strip() for f in str(features).split(',')]
                                for feat_name in feature_names:
                                    try:
                                        component.features.add(Features.objects.get(name=feat_name))
                                    except Features.DoesNotExist:
                                        print(f"Row {i+1}: Feature '{feat_name}' not found")
                            
                            print(f"Component {component.name} created")
                        else:
                            print(f"Row {i+1}: Skipping create - missing required field (name)")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand}' not found, skipping create")
            else:
                print(f"Row {i+1}: Skipping create - missing sku or brand")

