import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()
from pathlib import Path
from toolanalysis.models import ComponentAttributes, Components, Attributes, Brands
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
        # Component identification: brand + sku
        brand_name = get_col(row, 'brand')
        sku = get_col(row, 'sku')
        # Attribute identification: name
        attribute_name = get_col(row, 'attribute')
        # Optional value field
        value = get_col(row, 'value')
        
        if action == 'delete':
            if brand_name and sku and attribute_name:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    attribute = Attributes.objects.get(name=attribute_name)
                    
                    # Build query - value must match if provided, or be None/empty
                    query = {
                        'component': component,
                        'attribute': attribute
                    }
                    if value is not None:
                        query['value'] = str(value) if value else None
                    else:
                        # If value is not provided, we'll try to match None or empty string
                        # But since unique_together includes value, we need an exact match
                        # So if value not provided in Excel, we can't safely delete without knowing which one
                        print(f"Row {i+1}: Warning - value not provided, cannot uniquely identify ComponentAttribute to delete. Skipping.")
                        continue
                    
                    component_attribute = ComponentAttributes.objects.get(**query)
                    component_attribute.delete()
                    print(f"ComponentAttribute {component.name} - {attribute.name} (value: {value}) deleted")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component with SKU '{sku}' and brand '{brand_name}' not found")
                except Attributes.DoesNotExist:
                    print(f"Row {i+1}: Attribute '{attribute_name}' not found")
                except ComponentAttributes.DoesNotExist:
                    print(f"Row {i+1}: ComponentAttribute not found")
                except ComponentAttributes.MultipleObjectsReturned:
                    print(f"Row {i+1}: Multiple ComponentAttributes found (this shouldn't happen with unique_together). Skipping.")
            else:
                print(f"Row {i+1}: Skipping delete - missing required fields (brand, sku, or attribute)")
        elif action == 'purge':
            # Purge: Remove all ComponentAttributes records for this component
            if brand_name and sku:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    
                    # Get count of ComponentAttributes before purging
                    componentattributes_count = ComponentAttributes.objects.filter(component=component).count()
                    
                    # Delete all ComponentAttributes records for this component
                    ComponentAttributes.objects.filter(component=component).delete()
                    
                    print(f"Purged component {component.name}: Removed {componentattributes_count} ComponentAttributes records")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component with SKU '{sku}' and brand '{brand_name}' not found")
            else:
                print(f"Row {i+1}: Skipping purge - missing required fields (brand or sku)")
        elif action == 'update':
            if brand_name and sku and attribute_name:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    attribute = Attributes.objects.get(name=attribute_name)
                    
                    # For update, we need to match existing record by component + attribute + old value
                    # But we don't have old value in Excel, so we'll update by component + attribute
                    # If multiple exist, we can't safely update
                    if value is None:
                        # Try to find by component + attribute (might have multiple)
                        matches = ComponentAttributes.objects.filter(component=component, attribute=attribute)
                        if matches.count() == 1:
                            component_attribute = matches.first()
                            # Value stays as is since not provided
                            component_attribute.save()
                            print(f"ComponentAttribute {component.name} - {attribute.name} updated (value unchanged)")
                        elif matches.count() == 0:
                            # Doesn't exist, create it
                            ComponentAttributes.objects.create(component=component, attribute=attribute, value=None)
                            print(f"ComponentAttribute {component.name} - {attribute.name} created (was update action, but didn't exist)")
                        else:
                            print(f"Row {i+1}: Multiple ComponentAttributes found for component '{component.name}' and attribute '{attribute.name}'. Cannot update without value. Skipping.")
                    else:
                        # Value provided, match by component + attribute + value
                        query = {
                            'component': component,
                            'attribute': attribute,
                            'value': str(value) if value else None
                        }
                        try:
                            component_attribute = ComponentAttributes.objects.get(**query)
                            # Update value (but it's already set, so this is just confirming)
                            component_attribute.save()
                            print(f"ComponentAttribute {component.name} - {attribute.name} (value: {value}) updated")
                        except ComponentAttributes.DoesNotExist:
                            # Doesn't exist, create it
                            ComponentAttributes.objects.create(component=component, attribute=attribute, value=str(value) if value else None)
                            print(f"ComponentAttribute {component.name} - {attribute.name} (value: {value}) created (was update action, but didn't exist)")
                        except ComponentAttributes.MultipleObjectsReturned:
                            print(f"Row {i+1}: Multiple ComponentAttributes found (this shouldn't happen with unique_together). Skipping.")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found, skipping")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component with SKU '{sku}' and brand '{brand_name}' not found, skipping")
                except Attributes.DoesNotExist:
                    print(f"Row {i+1}: Attribute '{attribute_name}' not found, skipping")
            else:
                print(f"Row {i+1}: Skipping update - missing required fields (brand, sku, or attribute)")
        elif action == 'create':
            if brand_name and sku and attribute_name:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    attribute = Attributes.objects.get(name=attribute_name)
                    
                    # Build create data
                    create_data = {
                        'component': component,
                        'attribute': attribute
                    }
                    if value is not None:
                        create_data['value'] = str(value) if value else None
                    
                    # Check if it already exists (by unique_together: component, attribute, value)
                    query = {
                        'component': component,
                        'attribute': attribute,
                        'value': create_data.get('value')
                    }
                    try:
                        # ComponentAttribute exists, don't create duplicate
                        component_attribute = ComponentAttributes.objects.get(**query)
                        print(f"ComponentAttribute {component.name} - {attribute.name} (value: {value}) already exists, skipping create")
                    except ComponentAttributes.DoesNotExist:
                        # ComponentAttribute doesn't exist, create it
                        ComponentAttributes.objects.create(**create_data)
                        print(f"ComponentAttribute {component.name} - {attribute.name} (value: {value}) created")
                    except ComponentAttributes.MultipleObjectsReturned:
                        print(f"Row {i+1}: Multiple ComponentAttributes found (this shouldn't happen with unique_together). Skipping.")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found, skipping create")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component with SKU '{sku}' and brand '{brand_name}' not found, skipping create")
                except Attributes.DoesNotExist:
                    print(f"Row {i+1}: Attribute '{attribute_name}' not found, skipping create")
            else:
                print(f"Row {i+1}: Skipping create - missing required fields (brand, sku, or attribute)")
        else:
            print(f"Row {i+1}: Unknown action '{action}', skipping")

