import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()
from pathlib import Path
from toolanalysis.models import ComponentFeatures, Components, Features, Brands
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
        # Feature identification: name
        feature_name = get_col(row, 'feature')
        # Optional value field
        value = get_col(row, 'value')
        
        if action == 'delete':
            if brand_name and sku and feature_name:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    feature = Features.objects.get(name=feature_name)
                    component_feature = ComponentFeatures.objects.get(component=component, feature=feature)
                    component_feature.delete()
                    # Also remove from the ManyToMany relationship
                    component.features.remove(feature)
                    print(f"ComponentFeature {component.name} - {feature.name} deleted")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component with SKU '{sku}' and brand '{brand_name}' not found")
                except Features.DoesNotExist:
                    print(f"Row {i+1}: Feature '{feature_name}' not found")
                except ComponentFeatures.DoesNotExist:
                    print(f"Row {i+1}: ComponentFeature not found")
            else:
                print(f"Row {i+1}: Skipping delete - missing required fields (brand, sku, or feature)")
        elif action == 'purge':
            # Purge: Remove all features from component and all ComponentFeatures records
            if brand_name and sku:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    
                    # Get count of features before purging
                    features_count = component.features.count()
                    componentfeatures_count = ComponentFeatures.objects.filter(component=component).count()
                    
                    # Remove all features from ManyToMany relationship
                    component.features.clear()
                    
                    # Delete all ComponentFeatures records for this component
                    ComponentFeatures.objects.filter(component=component).delete()
                    
                    print(f"Purged component {component.name}: Removed {features_count} features from ManyToMany and {componentfeatures_count} ComponentFeatures records")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component with SKU '{sku}' and brand '{brand_name}' not found")
            else:
                print(f"Row {i+1}: Skipping purge - missing required fields (brand or sku)")
        elif action == 'update':
            if brand_name and sku and feature_name:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    feature = Features.objects.get(name=feature_name)
                    try:
                        component_feature = ComponentFeatures.objects.get(component=component, feature=feature)
                        # Update existing ComponentFeature
                        if value is not None:
                            component_feature.value = str(value) if value else None
                        component_feature.save()
                        # Ensure feature is in the ManyToMany relationship (add is idempotent)
                        component.features.add(feature)
                        print(f"ComponentFeature {component.name} - {feature.name} updated")
                    except ComponentFeatures.DoesNotExist:
                        # ComponentFeature doesn't exist, create it
                        create_data = {
                            'component': component,
                            'feature': feature
                        }
                        if value is not None:
                            create_data['value'] = str(value) if value else None
                        ComponentFeatures.objects.create(**create_data)
                        # Also add to the ManyToMany relationship
                        component.features.add(feature)
                        print(f"ComponentFeature {component.name} - {feature.name} created (was update action, but didn't exist)")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found, skipping")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component with SKU '{sku}' and brand '{brand_name}' not found, skipping")
                except Features.DoesNotExist:
                    print(f"Row {i+1}: Feature '{feature_name}' not found, skipping")
            else:
                print(f"Row {i+1}: Skipping update - missing required fields (brand, sku, or feature)")
        elif action == 'create':
            if brand_name and sku and feature_name:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    feature = Features.objects.get(name=feature_name)
                    try:
                        # ComponentFeature exists, update it instead
                        component_feature = ComponentFeatures.objects.get(component=component, feature=feature)
                        if value is not None:
                            component_feature.value = str(value) if value else None
                        component_feature.save()
                        # Ensure feature is in the ManyToMany relationship (add is idempotent)
                        component.features.add(feature)
                        print(f"ComponentFeature {component.name} - {feature.name} updated (was create action, but already existed)")
                    except ComponentFeatures.DoesNotExist:
                        # ComponentFeature doesn't exist, create it
                        create_data = {
                            'component': component,
                            'feature': feature
                        }
                        if value is not None:
                            create_data['value'] = str(value) if value else None
                        ComponentFeatures.objects.create(**create_data)
                        # Also add to the ManyToMany relationship
                        component.features.add(feature)
                        print(f"ComponentFeature {component.name} - {feature.name} created")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found, skipping create")
                except Components.DoesNotExist:
                    print(f"Row {i+1}: Component with SKU '{sku}' and brand '{brand_name}' not found, skipping create")
                except Features.DoesNotExist:
                    print(f"Row {i+1}: Feature '{feature_name}' not found, skipping create")
            else:
                print(f"Row {i+1}: Skipping create - missing required fields (brand, sku, or feature)")
        else:
            print(f"Row {i+1}: Unknown action '{action}', skipping")

