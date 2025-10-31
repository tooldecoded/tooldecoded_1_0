import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()
from pathlib import Path
from toolanalysis.models import (
    Products, Components, ComponentFeatures, ComponentAttributes,
    ProductComponents, ProductAccessories, ProductSpecifications, ProductImages,
    Attributes, Features, Categories, Subcategories, ItemTypes,
    MotorTypes, ListingTypes, Brands, BatteryVoltages, BatteryPlatforms,
    Retailers, Statuses, ProductLines, PriceListings
)
import pandas as pd
from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import scrolledtext
from datetime import date

# ============================================================================
# Column requirements mapping (defined early for UI use)
# ============================================================================

COLUMNS_MAP = {
    'product': {
        'required': ['action', 'recordtype', 'brand', 'sku'],
        'optional': ['name', 'description', 'image', 'listingtype', 'status', 
                    'motortype', 'releasedate', 'discontinueddate', 'isaccessory',
                    'itemtypefullname', 'subcategoryfullname', 'categoryfullname',
                    'batteryplatform', 'batteryvoltage', 'features'],
        'description': 'Products - Main product records'
    },
    'component': {
        'required': ['action', 'recordtype', 'brand', 'sku'],
        'optional': ['name', 'description', 'image', 'listingtype', 'motortype',
                    'is_featured', 'standalone_price', 'showcase_priority', 'isaccessory',
                    'itemtypefullname', 'subcategoryfullname', 'categoryfullname',
                    'batteryplatform', 'batteryvoltage', 'productline', 'features'],
        'description': 'Components - Individual component records'
    },
    'componentfeature': {
        'required': ['action', 'recordtype', 'brand', 'component_sku', 'feature'],
        'optional': ['value'],
        'description': 'ComponentFeatures - Features associated with components'
    },
    'componentattribute': {
        'required': ['action', 'recordtype', 'brand', 'component_sku', 'attribute'],
        'optional': ['value'],
        'description': 'ComponentAttributes - Attributes associated with components'
    },
    'productcomponent': {
        'required': ['action', 'recordtype', 'brand', 'product_sku', 'component_sku'],
        'optional': ['component_brand', 'quantity'],
        'description': 'ProductComponents - Components that make up a product'
    },
    'productaccessory': {
        'required': ['action', 'recordtype', 'brand', 'product_sku', 'name'],
        'optional': ['quantity'],
        'description': 'ProductAccessories - Accessories for products'
    },
    'productspecification': {
        'required': ['action', 'recordtype', 'brand', 'product_sku', 'name'],
        'optional': ['value'],
        'description': 'ProductSpecifications - Specifications for products'
    },
    'productimage': {
        'required': ['action', 'recordtype', 'brand', 'product_sku', 'image'],
        'optional': [],
        'description': 'ProductImages - Image URLs/paths for products'
    },
    'attribute': {
        'required': ['action', 'recordtype', 'name'],
        'optional': ['unit', 'description', 'sortorder'],
        'description': 'Attributes - Attribute definitions'
    },
    'feature': {
        'required': ['action', 'recordtype', 'name'],
        'optional': ['description', 'sortorder'],
        'description': 'Features - Feature definitions'
    },
    'category': {
        'required': ['action', 'recordtype', 'fullname'],
        'optional': ['name', 'sortorder'],
        'description': 'Categories - Product categories'
    },
    'subcategory': {
        'required': ['action', 'recordtype', 'fullname'],
        'optional': ['name', 'sortorder', 'categoryfullname'],
        'description': 'Subcategories - Product subcategories'
    },
    'itemtype': {
        'required': ['action', 'recordtype', 'fullname'],
        'optional': ['name', 'sortorder', 'categoryfullname', 'subcategoryfullname', 'attribute'],
        'description': 'ItemTypes - Item type definitions'
    },
    'motortype': {
        'required': ['action', 'recordtype', 'name'],
        'optional': ['sortorder'],
        'description': 'MotorTypes - Motor type definitions'
    },
    'listingtype': {
        'required': ['action', 'recordtype', 'name'],
        'optional': ['retailer'],
        'description': 'ListingTypes - Listing type definitions'
    },
    'brand': {
        'required': ['action', 'recordtype', 'name'],
        'optional': ['color', 'logo', 'sortorder'],
        'description': 'Brands - Brand definitions'
    },
    'batteryvoltage': {
        'required': ['action', 'recordtype', 'value'],
        'optional': [],
        'description': 'BatteryVoltages - Battery voltage values'
    },
    'retailer': {
        'required': ['action', 'recordtype', 'name'],
        'optional': ['url', 'logo', 'sortorder'],
        'description': 'Retailers - Retailer definitions'
    },
    'status': {
        'required': ['action', 'recordtype', 'name'],
        'optional': ['color', 'icon', 'sortorder'],
        'description': 'Statuses - Status definitions'
    },
    'batteryplatform': {
        'required': ['action', 'recordtype', 'name'],
        'optional': ['brand', 'voltage'],
        'description': 'BatteryPlatforms - Battery platform definitions'
    },
    'productline': {
        'required': ['action', 'recordtype', 'name', 'brand'],
        'optional': ['description', 'image', 'batteryplatform', 'batteryvoltage'],
        'description': 'ProductLines - Product line definitions'
    },
    'pricelisting': {
        'required': ['action', 'recordtype', 'brand', 'product_sku', 'retailer', 'price'],
        'optional': ['retailer_sku', 'currency', 'url', 'datepulled'],
        'description': 'PriceListings - Price listings for products from retailers'
    },
}

def show_column_requirements(parent_window):
    """Show a dialog with column requirements for record types"""
    # Keep parent window withdrawn - don't show it
    # On Windows, if we set transient and then iconify the parent, the dialog also gets hidden
    try:
        parent_window.withdraw()  # Hide parent window
        parent_window.update_idletasks()
    except:
        pass
    
    help_dialog = tk.Toplevel(parent_window)
    help_dialog.title("Column Requirements Reference")
    help_dialog.geometry("700x600")
    
    # Center the dialog
    help_dialog.update_idletasks()
    x = (help_dialog.winfo_screenwidth() // 2) - (help_dialog.winfo_width() // 2)
    y = (help_dialog.winfo_screenheight() // 2) - (help_dialog.winfo_height() // 2)
    help_dialog.geometry(f"+{x}+{y}")
    
    # Create main frame with two panes BEFORE setting grab
    main_frame = tk.Frame(help_dialog)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Left pane: List of record types
    left_frame = tk.Frame(main_frame, width=200)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
    left_frame.pack_propagate(False)
    
    # Action types explanation (compact version)
    action_label = tk.Label(left_frame, text="Action Types:", font=("Arial", 9, "bold"))
    action_label.pack(pady=(5, 2))
    
    action_text = tk.Text(left_frame, wrap=tk.WORD, font=("Arial", 8), height=10, width=25, 
                         relief=tk.FLAT, bg=left_frame.cget('bg'), state=tk.DISABLED)
    action_text.pack(pady=(0, 5), padx=5, fill=tk.X)
    
    action_content = """• CREATE - New record
• UPDATE - Modify existing
• DELETE - Remove record
• PURGE - Clear fields"""
    
    action_text.config(state=tk.NORMAL)
    action_text.insert(1.0, action_content)
    action_text.config(state=tk.DISABLED)
    
    tk.Label(left_frame, text="Record Types:", font=("Arial", 10, "bold")).pack(pady=(10, 5))
    
    scrollbar_left = tk.Scrollbar(left_frame)
    scrollbar_left.pack(side=tk.RIGHT, fill=tk.Y)
    
    types_listbox = tk.Listbox(left_frame, yscrollcommand=scrollbar_left.set, font=("Arial", 9))
    scrollbar_left.config(command=types_listbox.yview)
    
    record_types = sorted(COLUMNS_MAP.keys())
    for rt in record_types:
        types_listbox.insert(tk.END, rt)
    types_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Right pane: Column details
    right_frame = tk.Frame(main_frame)
    right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    text_area = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, font=("Courier", 9), width=50, height=30)
    text_area.pack(fill=tk.BOTH, expand=True)
    
    def update_display(event=None):
        try:
            selection = types_listbox.curselection()
            text_area.delete(1.0, tk.END)
            
            if selection:
                recordtype = record_types[selection[0]]
                info = COLUMNS_MAP[recordtype]
                
                text_area.insert(tk.END, f"{'='*60}\n")
                text_area.insert(tk.END, f"Record Type: {recordtype}\n")
                text_area.insert(tk.END, f"{'='*60}\n\n")
                text_area.insert(tk.END, f"Description:\n{info['description']}\n\n")
                text_area.insert(tk.END, f"{'='*60}\n\n")
                text_area.insert(tk.END, "REQUIRED COLUMNS:\n")
                text_area.insert(tk.END, "-" * 30 + "\n")
                for col in info['required']:
                    text_area.insert(tk.END, f"  • {col}\n")
                text_area.insert(tk.END, f"\n{'='*60}\n\n")
                if info['optional']:
                    text_area.insert(tk.END, "OPTIONAL COLUMNS:\n")
                    text_area.insert(tk.END, "-" * 30 + "\n")
                    for col in info['optional']:
                        text_area.insert(tk.END, f"  • {col}\n")
                else:
                    text_area.insert(tk.END, "OPTIONAL COLUMNS:\n")
                    text_area.insert(tk.END, "-" * 30 + "\n")
                    text_area.insert(tk.END, "  (none)\n")
        except Exception as e:
            text_area.delete(1.0, tk.END)
            text_area.insert(tk.END, f"Error displaying column info: {str(e)}")
    
    types_listbox.bind('<<ListboxSelect>>', update_display)
    
    # Close and Exit buttons
    button_frame = tk.Frame(help_dialog)
    button_frame.pack(pady=10)
    
    close_button = tk.Button(button_frame, text="Close and Continue", command=lambda: help_dialog.destroy(), width=20)
    close_button.pack(side=tk.LEFT, padx=5)
    
    exit_button = tk.Button(button_frame, text="Exit Application", command=lambda: sys.exit(0), width=20)
    exit_button.pack(side=tk.LEFT, padx=5)
    
    # Set up window close protocol
    def on_close():
        help_dialog.destroy()
    
    help_dialog.protocol("WM_DELETE_WINDOW", on_close)
    
    # Make sure dialog is fully rendered and shown BEFORE setting grab
    help_dialog.update_idletasks()
    help_dialog.update()
    
    # Initialize display
    if record_types:
        types_listbox.selection_set(0)
        help_dialog.update()
        try:
            update_display()
        except Exception as e:
            print(f"Warning: Could not initialize display: {e}")
    
    # Ensure dialog is fully visible and on top
    help_dialog.lift()
    help_dialog.focus_force()
    help_dialog.update()
    help_dialog.update_idletasks()
    
    # Set grab for modal behavior (don't use transient with hidden parent on Windows)
    # On Windows, transient + iconify causes the dialog to be hidden
    help_dialog.grab_set()
    
    # Update one more time after grab
    help_dialog.update()
    help_dialog.update_idletasks()
    
    # Parent is already withdrawn - don't iconify it (would hide dialog on Windows)
    
    # Wait for dialog to close - this blocks until window is destroyed
    try:
        help_dialog.wait_window()
    except Exception as e:
        print(f"Error in wait_window: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: keep updating until window is destroyed
        while help_dialog.winfo_exists():
            try:
                parent_window.update()
                help_dialog.update()
                import time
                time.sleep(0.1)
            except:
                break
    
    # Restore parent window after dialog closes (for file dialogs)
    try:
        parent_window.deiconify()
        parent_window.update_idletasks()
    except:
        pass

# Initialize root window
root = tk.Tk()
root.title("Import Master")
# Withdraw root window immediately - we don't want it visible
root.withdraw()

# Update to ensure window is ready
root.update_idletasks()

# Show column requirements dialog first - root must stay alive for Toplevel to work
try:
    print("Showing column requirements dialog...")
    show_column_requirements(root)
    print("Column requirements dialog closed.")
except Exception as e:
    import traceback
    print(f"Error showing column requirements dialog: {str(e)}")
    traceback.print_exc()
    # Continue anyway if dialog fails - user can still proceed with import

# Make sure root is deiconified for file dialogs
root.deiconify()
root.update_idletasks()

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
    
    # Create dialog for sheet selection (multiple selection enabled)
    selected_sheets = None
    
    def on_select():
        selection = listbox.curselection()
        if selection:
            dialog.selected_sheets = [sheet_names[idx] for idx in selection]
            dialog.destroy()
        else:
            messagebox.showwarning("No Selection", "Please select at least one sheet first.")
    
    def on_select_all():
        listbox.selection_set(0, tk.END)
    
    def on_deselect_all():
        listbox.selection_clear(0, tk.END)
    
    dialog = tk.Toplevel(root)
    dialog.title("Select Sheets/Tabs (Multiple Selection)")
    dialog.geometry("450x400")
    dialog.selected_sheets = None  # Initialize before creating widgets
    
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
    label = tk.Label(dialog, text="Select one or more sheets to import:\n(Ctrl+Click or Shift+Click for multiple)", font=("Arial", 10))
    label.pack(pady=10)
    
    # Listbox with scrollbar (EXTENDED mode for multiple selection)
    frame = tk.Frame(dialog)
    frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
    
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 10), selectmode=tk.EXTENDED)
    scrollbar.config(command=listbox.yview)
    
    for sheet_name in sheet_names:
        listbox.insert(tk.END, sheet_name)
    
    listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    if sheet_names:  # Only if there are sheets
        listbox.selection_set(0)  # Select first item by default
    
    # Buttons
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=10)
    
    select_all_button = tk.Button(button_frame, text="Select All", command=on_select_all, width=10)
    select_all_button.pack(side=tk.LEFT, padx=5)
    
    deselect_all_button = tk.Button(button_frame, text="Deselect All", command=on_deselect_all, width=10)
    deselect_all_button.pack(side=tk.LEFT, padx=5)
    
    ok_button = tk.Button(button_frame, text="OK", command=on_select, width=10)
    ok_button.pack(side=tk.LEFT, padx=5)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=lambda: (setattr(dialog, 'selected_sheets', None), dialog.destroy()), width=10)
    cancel_button.pack(side=tk.LEFT, padx=5)
    
    dialog.transient(root)
    dialog.grab_set()
    dialog.focus_set()
    
    # Wait for dialog to close
    root.deiconify()  # Make sure root is available (even if hidden)
    dialog.wait_window()
    
    selected_sheets = dialog.selected_sheets
    
    if not selected_sheets:
        print("No sheets selected. Exiting...")
        sys.exit(0)
    
    print(f"\nSelected {len(selected_sheets)} sheet(s): {', '.join(selected_sheets)}")
    
except Exception as e:
    print(f"Error reading Excel file: {str(e)}")
    sys.exit(1)

# Clean up root window
root.destroy()

# Helper function to safely get column value
def get_col(row, col_name, df):
    """Get column value if column exists and is not NaN, otherwise return None"""
    if col_name in df.columns:
        value = row[col_name]
        return value if pd.notna(value) else None
    return None

# ============================================================================
# Helper function to get expected column names for a record type
# ============================================================================

def get_expected_columns(recordtype):
    """
    Returns the expected column names for a given record type.
    
    Args:
        recordtype (str): The record type name (e.g., 'product', 'component', etc.)
    
    Returns:
        dict: A dictionary with keys:
            - 'required': List of required column names (always needed)
            - 'optional': List of optional column names
            - 'description': Brief description of what this record type is
    
    Example:
        >>> cols = get_expected_columns('product')
        >>> print(cols['required'])
        ['action', 'recordtype', 'brand', 'sku']
    """
    recordtype_lower = str(recordtype).lower().strip()
    
    if recordtype_lower in COLUMNS_MAP:
        return COLUMNS_MAP[recordtype_lower]
    else:
        return {
            'required': ['action', 'recordtype'],
            'optional': [],
            'description': f'Unknown record type: {recordtype}'
        }


# ============================================================================
# Handler functions for each record type
# ============================================================================

def handle_product(row, i, action, df, sheet_name=""):
    """Handle Product records"""
    sku = get_col(row, 'sku', df)
    brand = get_col(row, 'brand', df)
    name = get_col(row, 'name', df)
    description = get_col(row, 'description', df)
    image = get_col(row, 'image', df)
    listingtype = get_col(row, 'listingtype', df)
    itemtype = get_col(row, 'itemtypefullname', df)
    subcategory = get_col(row, 'subcategoryfullname', df)
    category = get_col(row, 'categoryfullname', df)
    batteryplatform = get_col(row, 'batteryplatform', df)
    batteryvoltage = get_col(row, 'batteryvoltage', df)
    status = get_col(row, 'status', df)
    motortype = get_col(row, 'motortype', df)
    features = get_col(row, 'features', df)
    releasedate = get_col(row, 'releasedate', df)
    discontinueddate = get_col(row, 'discontinueddate', df)
    isaccessory = get_col(row, 'isaccessory', df)
    
    if action == 'delete':
        if sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=sku, brand=brand_obj)
                product.delete()
                print(f"Row {i+1}: Product {product.name} deleted")
            except Brands.DoesNotExist:
                print(f"Row {i+1}: Brand '{brand}' not found")
            except Products.DoesNotExist:
                print(f"Row {i+1}: Product not found")
    elif action == 'update':
        if sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=sku, brand=brand_obj)
                
                if name is not None:
                    product.name = name
                if description is not None:
                    product.description = description
                if image is not None:
                    product.image = image
                if listingtype:
                    try:
                        product.listingtype = ListingTypes.objects.get(name=listingtype)
                    except ListingTypes.DoesNotExist:
                        print(f"Row {i+1}: ListingType '{listingtype}' not found, skipping")
                if status:
                    try:
                        product.status = Statuses.objects.get(name=status)
                    except Statuses.DoesNotExist:
                        print(f"Row {i+1}: Status '{status}' not found, skipping")
                if motortype:
                    try:
                        product.motortype = MotorTypes.objects.get(name=motortype)
                    except MotorTypes.DoesNotExist:
                        print(f"Row {i+1}: MotorType '{motortype}' not found, skipping")
                if releasedate:
                    product.releasedate = pd.to_datetime(releasedate).date() if isinstance(releasedate, str) else releasedate
                if discontinueddate:
                    product.discontinueddate = pd.to_datetime(discontinueddate).date() if isinstance(discontinueddate, str) else discontinueddate
                if isaccessory is not None:
                    product.isaccessory = bool(isaccessory)
                
                # ManyToMany fields - use .add() only
                if itemtype:
                    try:
                        product.itemtypes.add(ItemTypes.objects.get(fullname=itemtype))
                    except ItemTypes.DoesNotExist:
                        print(f"Row {i+1}: ItemType '{itemtype}' not found, skipping")
                if subcategory:
                    try:
                        product.subcategories.add(Subcategories.objects.get(fullname=subcategory))
                    except Subcategories.DoesNotExist:
                        print(f"Row {i+1}: Subcategory '{subcategory}' not found, skipping")
                if category:
                    try:
                        product.categories.add(Categories.objects.get(fullname=category))
                    except Categories.DoesNotExist:
                        print(f"Row {i+1}: Category '{category}' not found, skipping")
                if batteryplatform:
                    try:
                        product.batteryplatforms.add(BatteryPlatforms.objects.get(name=batteryplatform))
                    except BatteryPlatforms.DoesNotExist:
                        print(f"Row {i+1}: BatteryPlatform '{batteryplatform}' not found, skipping")
                if batteryvoltage:
                    try:
                        product.batteryvoltages.add(BatteryVoltages.objects.get(value=int(batteryvoltage)))
                    except BatteryVoltages.DoesNotExist:
                        print(f"Row {i+1}: BatteryVoltage '{batteryvoltage}' not found, skipping")
                if features:
                    feature_names = [f.strip() for f in str(features).split(',')]
                    for feat_name in feature_names:
                        try:
                            product.features.add(Features.objects.get(name=feat_name))
                        except Features.DoesNotExist:
                            print(f"Row {i+1}: Feature '{feat_name}' not found")
                
                product.save()
                print(f"Row {i+1}: Product {product.name} updated")
            except Products.DoesNotExist:
                print(f"Row {i+1}: Product not found for update")
    elif action == 'purge':
        if sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=sku, brand=brand_obj)
                
                columns_to_purge = [col for col in df.columns if col.lower() not in ['action', 'brand', 'sku', 'recordtype']]
                purged_fields = []
                
                for col_name in columns_to_purge:
                    try:
                        if col_name == 'name':
                            product.name = ''
                            purged_fields.append('name')
                        elif col_name == 'description':
                            product.description = None
                            purged_fields.append('description')
                        elif col_name == 'image':
                            product.image = None
                            purged_fields.append('image')
                        elif col_name == 'listingtype':
                            product.listingtype = None
                            purged_fields.append('listingtype')
                        elif col_name == 'status':
                            product.status = None
                            purged_fields.append('status')
                        elif col_name == 'motortype':
                            product.motortype = None
                            purged_fields.append('motortype')
                        elif col_name == 'releasedate':
                            product.releasedate = None
                            purged_fields.append('releasedate')
                        elif col_name == 'discontinueddate':
                            product.discontinueddate = None
                            purged_fields.append('discontinueddate')
                        elif col_name == 'isaccessory':
                            product.isaccessory = False
                            purged_fields.append('isaccessory')
                        elif col_name in ['itemtypefullname', 'itemtype']:
                            product.itemtypes.clear()
                            purged_fields.append('itemtypes')
                        elif col_name in ['subcategoryfullname', 'subcategory']:
                            product.subcategories.clear()
                            purged_fields.append('subcategories')
                        elif col_name in ['categoryfullname', 'category']:
                            product.categories.clear()
                            purged_fields.append('categories')
                        elif col_name == 'batteryplatform':
                            product.batteryplatforms.clear()
                            purged_fields.append('batteryplatforms')
                        elif col_name == 'batteryvoltage':
                            product.batteryvoltages.clear()
                            purged_fields.append('batteryvoltages')
                        elif col_name == 'features':
                            product.features.clear()
                            purged_fields.append('features')
                    except Exception as e:
                        print(f"Row {i+1}: Error purging field '{col_name}': {str(e)}")
                
                product.save()
                if purged_fields:
                    print(f"Row {i+1}: Product {product.name} purged: {', '.join(purged_fields)}")
            except Brands.DoesNotExist:
                print(f"Row {i+1}: Brand '{brand}' not found")
            except Products.DoesNotExist:
                print(f"Row {i+1}: Product not found")
    elif action == 'create':
        if sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                try:
                    product = Products.objects.get(sku=sku, brand=brand_obj)
                    print(f"Row {i+1}: Product already exists, updating instead")
                    handle_product(row, i, 'update', df, sheet_name)
                except Products.DoesNotExist:
                    create_data = {}
                    if name is not None:
                        create_data['name'] = name
                    if description is not None:
                        create_data['description'] = description
                    if brand:
                        create_data['brand'] = brand_obj
                    if sku:
                        create_data['sku'] = sku
                    if image is not None:
                        create_data['image'] = image
                    if listingtype:
                        try:
                            create_data['listingtype'] = ListingTypes.objects.get(name=listingtype)
                        except ListingTypes.DoesNotExist:
                            print(f"Row {i+1}: ListingType '{listingtype}' not found, skipping")
                    if status:
                        try:
                            create_data['status'] = Statuses.objects.get(name=status)
                        except Statuses.DoesNotExist:
                            print(f"Row {i+1}: Status '{status}' not found, skipping")
                    if motortype:
                        try:
                            create_data['motortype'] = MotorTypes.objects.get(name=motortype)
                        except MotorTypes.DoesNotExist:
                            print(f"Row {i+1}: MotorType '{motortype}' not found, skipping")
                    if releasedate:
                        create_data['releasedate'] = pd.to_datetime(releasedate).date() if isinstance(releasedate, str) else releasedate
                    if discontinueddate:
                        create_data['discontinueddate'] = pd.to_datetime(discontinueddate).date() if isinstance(discontinueddate, str) else discontinueddate
                    if isaccessory is not None:
                        create_data['isaccessory'] = bool(isaccessory)
                    
                    if 'name' in create_data and 'brand' in create_data:
                        product = Products.objects.create(**create_data)
                        
                        # Set ManyToMany fields
                        if itemtype:
                            try:
                                product.itemtypes.add(ItemTypes.objects.get(fullname=itemtype))
                            except ItemTypes.DoesNotExist:
                                print(f"Row {i+1}: ItemType '{itemtype}' not found, skipping")
                        if subcategory:
                            try:
                                product.subcategories.add(Subcategories.objects.get(fullname=subcategory))
                            except Subcategories.DoesNotExist:
                                print(f"Row {i+1}: Subcategory '{subcategory}' not found, skipping")
                        if category:
                            try:
                                product.categories.add(Categories.objects.get(fullname=category))
                            except Categories.DoesNotExist:
                                print(f"Row {i+1}: Category '{category}' not found, skipping")
                        if batteryplatform:
                            try:
                                product.batteryplatforms.add(BatteryPlatforms.objects.get(name=batteryplatform))
                            except BatteryPlatforms.DoesNotExist:
                                print(f"Row {i+1}: BatteryPlatform '{batteryplatform}' not found, skipping")
                        if batteryvoltage:
                            try:
                                product.batteryvoltages.add(BatteryVoltages.objects.get(value=int(batteryvoltage)))
                            except BatteryVoltages.DoesNotExist:
                                print(f"Row {i+1}: BatteryVoltage '{batteryvoltage}' not found, skipping")
                        if features:
                            feature_names = [f.strip() for f in str(features).split(',')]
                            for feat_name in feature_names:
                                try:
                                    product.features.add(Features.objects.get(name=feat_name))
                                except Features.DoesNotExist:
                                    print(f"Row {i+1}: Feature '{feat_name}' not found")
                        
                        print(f"Row {i+1}: Product {product.name} created")
            except Brands.DoesNotExist:
                print(f"Row {i+1}: Brand '{brand}' not found")

def handle_component(row, i, action, df, sheet_name=""):
    """Handle Component records"""
    sku = get_col(row, 'sku', df)
    brand = get_col(row, 'brand', df)
    name = get_col(row, 'name', df)
    description = get_col(row, 'description', df)
    image = get_col(row, 'image', df)
    listingtype = get_col(row, 'listingtype', df)
    itemtype = get_col(row, 'itemtypefullname', df)
    subcategory = get_col(row, 'subcategoryfullname', df)
    category = get_col(row, 'categoryfullname', df)
    batteryplatform = get_col(row, 'batteryplatform', df)
    batteryvoltage = get_col(row, 'batteryvoltage', df)
    productline = get_col(row, 'productline', df)
    motortype = get_col(row, 'motortype', df)
    features = get_col(row, 'features', df)
    is_featured = get_col(row, 'is_featured', df)
    standalone_price = get_col(row, 'standalone_price', df)
    showcase_priority = get_col(row, 'showcase_priority', df)
    isaccessory = get_col(row, 'isaccessory', df)
    
    if action == 'delete':
        if sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=sku, brand=brand_obj)
                component.delete()
                print(f"Row {i+1}: Component {component.name} deleted")
            except Brands.DoesNotExist:
                print(f"Row {i+1}: Brand '{brand}' not found")
            except Components.DoesNotExist:
                print(f"Row {i+1}: Component not found")
    elif action == 'update':
        if sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=sku, brand=brand_obj)
                
                if name is not None:
                    component.name = name
                if description is not None:
                    component.description = description
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
                    component.standalone_price = float(standalone_price)
                if showcase_priority is not None:
                    component.showcase_priority = int(showcase_priority)
                if isaccessory is not None:
                    component.isaccessory = bool(isaccessory)
                
                # ManyToMany fields - use .add() only
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
                        component.batteryvoltages.add(BatteryVoltages.objects.get(value=int(batteryvoltage)))
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
                print(f"Row {i+1}: Component {component.name} updated")
            except Components.DoesNotExist:
                print(f"Row {i+1}: Component not found for update")
    elif action == 'purge':
        if sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=sku, brand=brand_obj)
                
                columns_to_purge = [col for col in df.columns if col.lower() not in ['action', 'brand', 'sku', 'recordtype']]
                purged_fields = []
                
                for col_name in columns_to_purge:
                    try:
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
                        elif col_name in ['itemtypefullname', 'itemtype']:
                            component.itemtypes.clear()
                            purged_fields.append('itemtypes')
                        elif col_name in ['subcategoryfullname', 'subcategory']:
                            component.subcategories.clear()
                            purged_fields.append('subcategories')
                        elif col_name in ['categoryfullname', 'category']:
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
                    print(f"Row {i+1}: Component {component.name} purged: {', '.join(purged_fields)}")
            except Brands.DoesNotExist:
                print(f"Row {i+1}: Brand '{brand}' not found")
            except Components.DoesNotExist:
                print(f"Row {i+1}: Component not found")
    elif action == 'create':
        if sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                try:
                    component = Components.objects.get(sku=sku, brand=brand_obj)
                    print(f"Row {i+1}: Component already exists, updating instead")
                    handle_component(row, i, 'update', df, sheet_name)
                except Components.DoesNotExist:
                    create_data = {}
                    if name is not None:
                        create_data['name'] = name
                    if description is not None:
                        create_data['description'] = description
                    if brand:
                        create_data['brand'] = brand_obj
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
                        create_data['standalone_price'] = float(standalone_price)
                    if showcase_priority is not None:
                        create_data['showcase_priority'] = int(showcase_priority)
                    if isaccessory is not None:
                        create_data['isaccessory'] = bool(isaccessory)
                    
                    if 'name' in create_data and 'brand' in create_data:
                        component = Components.objects.create(**create_data)
                        
                        # Set ManyToMany fields
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
                                component.batteryvoltages.add(BatteryVoltages.objects.get(value=int(batteryvoltage)))
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
                        
                        print(f"Row {i+1}: Component {component.name} created")
            except Brands.DoesNotExist:
                print(f"Row {i+1}: Brand '{brand}' not found")

# Due to length constraints, I'll continue with the remaining handlers in a condensed form
# For joining tables and simple models, the pattern is similar

def handle_componentfeature(row, i, action, df, sheet_name=""):
    """Handle ComponentFeature records"""
    brand = get_col(row, 'brand', df)
    component_sku = get_col(row, 'component_sku', df)
    feature = get_col(row, 'feature', df)
    value = get_col(row, 'value', df)
    
    if action == 'delete':
        if brand and component_sku and feature:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                feature_obj = Features.objects.get(name=feature)
                try:
                    comp_feature = ComponentFeatures.objects.get(component=component, feature=feature_obj)
                    component.features.remove(feature_obj)
                    comp_feature.delete()
                    print(f"Row {i+1}: ComponentFeature deleted")
                except ComponentFeatures.DoesNotExist:
                    print(f"Row {i+1}: ComponentFeature not found")
            except (Brands.DoesNotExist, Components.DoesNotExist, Features.DoesNotExist) as e:
                print(f"Row {i+1}: {type(e).__name__}")
    elif action == 'update':
        if brand and component_sku and feature:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                feature_obj = Features.objects.get(name=feature)
                try:
                    comp_feature = ComponentFeatures.objects.get(component=component, feature=feature_obj)
                    if value is not None:
                        comp_feature.value = value
                    comp_feature.save()
                    print(f"Row {i+1}: ComponentFeature updated")
                except ComponentFeatures.DoesNotExist:
                    comp_feature = ComponentFeatures.objects.create(component=component, feature=feature_obj, value=value)
                    component.features.add(feature_obj)
                    print(f"Row {i+1}: ComponentFeature created (was update)")
            except (Brands.DoesNotExist, Components.DoesNotExist, Features.DoesNotExist) as e:
                print(f"Row {i+1}: {type(e).__name__}")
    elif action == 'purge':
        if brand and component_sku:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                component.features.clear()
                ComponentFeatures.objects.filter(component=component).delete()
                print(f"Row {i+1}: All ComponentFeatures purged for component")
            except (Brands.DoesNotExist, Components.DoesNotExist) as e:
                print(f"Row {i+1}: {type(e).__name__}")
    elif action == 'create':
        if brand and component_sku and feature:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                feature_obj = Features.objects.get(name=feature)
                try:
                    ComponentFeatures.objects.get(component=component, feature=feature_obj)
                    print(f"Row {i+1}: ComponentFeature already exists")
                except ComponentFeatures.DoesNotExist:
                    comp_feature = ComponentFeatures.objects.create(component=component, feature=feature_obj, value=value)
                    component.features.add(feature_obj)
                    print(f"Row {i+1}: ComponentFeature created")
            except (Brands.DoesNotExist, Components.DoesNotExist, Features.DoesNotExist) as e:
                print(f"Row {i+1}: {type(e).__name__}")

def handle_componentattribute(row, i, action, df, sheet_name=""):
    """Handle ComponentAttribute records"""
    brand = get_col(row, 'brand', df)
    component_sku = get_col(row, 'component_sku', df)
    attribute = get_col(row, 'attribute', df)
    value = get_col(row, 'value', df)
    
    if action == 'delete':
        if brand and component_sku and attribute:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                try:
                    if value:
                        attr_obj = Attributes.objects.get(name=attribute, unit=Attributes.objects.filter(name=attribute).first().unit if Attributes.objects.filter(name=attribute).exists() else None)
                        comp_attr = ComponentAttributes.objects.get(component=component, attribute=attr_obj, value=value)
                    else:
                        attr_obj = Attributes.objects.get(name=attribute)
                        comp_attr = ComponentAttributes.objects.filter(component=component, attribute=attr_obj).first()
                    if comp_attr:
                        comp_attr.delete()
                        print(f"Row {i+1}: ComponentAttribute deleted")
                except ComponentAttributes.DoesNotExist:
                    print(f"Row {i+1}: ComponentAttribute not found")
            except (Brands.DoesNotExist, Components.DoesNotExist, Attributes.DoesNotExist) as e:
                print(f"Row {i+1}: {type(e).__name__}")
    elif action in ['update', 'create']:
        if brand and component_sku and attribute:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                attr_obj = Attributes.objects.get(name=attribute)
                try:
                    if value:
                        comp_attr = ComponentAttributes.objects.get(component=component, attribute=attr_obj, value=value)
                    else:
                        comp_attr = ComponentAttributes.objects.filter(component=component, attribute=attr_obj).first()
                    if comp_attr:
                        if value is not None:
                            comp_attr.value = value
                        comp_attr.save()
                        print(f"Row {i+1}: ComponentAttribute updated")
                except ComponentAttributes.DoesNotExist:
                    ComponentAttributes.objects.create(component=component, attribute=attr_obj, value=value)
                    print(f"Row {i+1}: ComponentAttribute created")
            except (Brands.DoesNotExist, Components.DoesNotExist, Attributes.DoesNotExist) as e:
                print(f"Row {i+1}: {type(e).__name__}")
    elif action == 'purge':
        if brand and component_sku:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                ComponentAttributes.objects.filter(component=component).delete()
                print(f"Row {i+1}: All ComponentAttributes purged")
            except (Brands.DoesNotExist, Components.DoesNotExist) as e:
                print(f"Row {i+1}: {type(e).__name__}")

def handle_productcomponent(row, i, action, df, sheet_name=""):
    """Handle ProductComponent records"""
    brand = get_col(row, 'brand', df)
    product_sku = get_col(row, 'product_sku', df)
    component_brand = get_col(row, 'component_brand', df) or brand
    component_sku = get_col(row, 'component_sku', df)
    quantity = get_col(row, 'quantity', df) or 1
    
    if action == 'delete':
        if brand and product_sku and component_sku:
            try:
                product_brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=product_brand_obj)
                comp_brand_obj = Brands.objects.get(name=component_brand)
                component = Components.objects.get(sku=component_sku, brand=comp_brand_obj)
                try:
                    ProductComponents.objects.get(product=product, component=component).delete()
                    print(f"Row {i+1}: ProductComponent deleted")
                except ProductComponents.DoesNotExist:
                    print(f"Row {i+1}: ProductComponent not found")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action in ['update', 'create']:
        if brand and product_sku and component_sku:
            try:
                product_brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=product_brand_obj)
                comp_brand_obj = Brands.objects.get(name=component_brand)
                component = Components.objects.get(sku=component_sku, brand=comp_brand_obj)
                try:
                    prod_comp = ProductComponents.objects.get(product=product, component=component)
                    prod_comp.quantity = int(quantity)
                    prod_comp.save()
                    print(f"Row {i+1}: ProductComponent updated")
                except ProductComponents.DoesNotExist:
                    ProductComponents.objects.create(product=product, component=component, quantity=int(quantity))
                    print(f"Row {i+1}: ProductComponent created")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action == 'purge':
        if brand and product_sku:
            try:
                product_brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=product_brand_obj)
                ProductComponents.objects.filter(product=product).delete()
                print(f"Row {i+1}: All ProductComponents purged")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")

def handle_productaccessory(row, i, action, df, sheet_name=""):
    """Handle ProductAccessory records"""
    brand = get_col(row, 'brand', df)
    product_sku = get_col(row, 'product_sku', df)
    name = get_col(row, 'name', df)
    quantity = get_col(row, 'quantity', df) or 1
    
    if action == 'delete':
        if brand and product_sku and name:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                try:
                    ProductAccessories.objects.get(product=product, name=name).delete()
                    print(f"Row {i+1}: ProductAccessory deleted")
                except ProductAccessories.DoesNotExist:
                    print(f"Row {i+1}: ProductAccessory not found")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action in ['update', 'create']:
        if brand and product_sku and name:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                try:
                    prod_acc = ProductAccessories.objects.get(product=product, name=name)
                    prod_acc.quantity = int(quantity)
                    prod_acc.save()
                    print(f"Row {i+1}: ProductAccessory updated")
                except ProductAccessories.DoesNotExist:
                    ProductAccessories.objects.create(product=product, name=name, quantity=int(quantity))
                    print(f"Row {i+1}: ProductAccessory created")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action == 'purge':
        if brand and product_sku:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                ProductAccessories.objects.filter(product=product).delete()
                print(f"Row {i+1}: All ProductAccessories purged")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")

def handle_productspecification(row, i, action, df, sheet_name=""):
    """Handle ProductSpecification records"""
    brand = get_col(row, 'brand', df)
    product_sku = get_col(row, 'product_sku', df)
    name = get_col(row, 'name', df)
    value = get_col(row, 'value', df)
    
    if action == 'delete':
        if brand and product_sku and name:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                try:
                    ProductSpecifications.objects.get(product=product, name=name).delete()
                    print(f"Row {i+1}: ProductSpecification deleted")
                except ProductSpecifications.DoesNotExist:
                    print(f"Row {i+1}: ProductSpecification not found")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action in ['update', 'create']:
        if brand and product_sku and name:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                try:
                    prod_spec = ProductSpecifications.objects.get(product=product, name=name)
                    if value is not None:
                        prod_spec.value = value
                    prod_spec.save()
                    print(f"Row {i+1}: ProductSpecification updated")
                except ProductSpecifications.DoesNotExist:
                    ProductSpecifications.objects.create(product=product, name=name, value=value)
                    print(f"Row {i+1}: ProductSpecification created")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action == 'purge':
        if brand and product_sku:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                ProductSpecifications.objects.filter(product=product).delete()
                print(f"Row {i+1}: All ProductSpecifications purged")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")

def handle_productimage(row, i, action, df, sheet_name=""):
    """Handle ProductImage records"""
    brand = get_col(row, 'brand', df)
    product_sku = get_col(row, 'product_sku', df)
    image = get_col(row, 'image', df)
    
    if action == 'delete':
        if brand and product_sku and image:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                try:
                    ProductImages.objects.get(product=product, image=image).delete()
                    print(f"Row {i+1}: ProductImage deleted")
                except ProductImages.DoesNotExist:
                    print(f"Row {i+1}: ProductImage not found")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action in ['update', 'create']:
        if brand and product_sku and image:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                try:
                    ProductImages.objects.get(product=product, image=image)
                    print(f"Row {i+1}: ProductImage exists")
                except ProductImages.DoesNotExist:
                    ProductImages.objects.create(product=product, image=image)
                    print(f"Row {i+1}: ProductImage created")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action == 'purge':
        if brand and product_sku:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                ProductImages.objects.filter(product=product).delete()
                print(f"Row {i+1}: All ProductImages purged")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")

def handle_attribute(row, i, action, df, sheet_name=""):
    """Handle Attribute records"""
    name = get_col(row, 'name', df)
    unit = get_col(row, 'unit', df)
    description = get_col(row, 'description', df)
    sortorder = get_col(row, 'sortorder', df)
    
    if action == 'delete':
        if name:
            try:
                if unit:
                    attr = Attributes.objects.get(name=name, unit=unit)
                else:
                    attr = Attributes.objects.get(name=name, unit__isnull=True)
                attr.delete()
                print(f"Row {i+1}: Attribute {name} deleted")
            except Attributes.DoesNotExist:
                print(f"Row {i+1}: Attribute not found")
            except Attributes.MultipleObjectsReturned:
                print(f"Row {i+1}: Multiple Attributes found, cannot delete without unit")
    elif action == 'update':
        if name:
            try:
                if unit:
                    attr = Attributes.objects.get(name=name, unit=unit)
                else:
                    attr = Attributes.objects.get(name=name, unit__isnull=True)
                if description is not None:
                    attr.description = description
                if sortorder is not None:
                    attr.sortorder = int(sortorder)
                attr.save()
                print(f"Row {i+1}: Attribute {name} updated")
            except Attributes.DoesNotExist:
                print(f"Row {i+1}: Attribute not found")
            except Attributes.MultipleObjectsReturned:
                print(f"Row {i+1}: Multiple Attributes found")
    elif action == 'create':
        if name:
            try:
                if unit:
                    create_data = {'name': name, 'unit': unit}
                else:
                    create_data = {'name': name}
                if description is not None:
                    create_data['description'] = description
                if sortorder is not None:
                    create_data['sortorder'] = int(sortorder)
                Attributes.objects.create(**create_data)
                print(f"Row {i+1}: Attribute {name} created")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")

def handle_feature(row, i, action, df, sheet_name=""):
    """Handle Feature records"""
    name = get_col(row, 'name', df)
    description = get_col(row, 'description', df)
    sortorder = get_col(row, 'sortorder', df)
    
    if action == 'delete':
        if name:
            try:
                Features.objects.get(name=name).delete()
                print(f"Row {i+1}: Feature {name} deleted")
            except Features.DoesNotExist:
                print(f"Row {i+1}: Feature not found")
    elif action == 'update':
        if name:
            try:
                feat = Features.objects.get(name=name)
                if description is not None:
                    feat.description = description
                if sortorder is not None:
                    feat.sortorder = int(sortorder)
                feat.save()
                print(f"Row {i+1}: Feature {name} updated")
            except Features.DoesNotExist:
                print(f"Row {i+1}: Feature not found")
    elif action == 'create':
        if name:
            try:
                Features.objects.get(name=name)
                print(f"Row {i+1}: Feature {name} already exists")
            except Features.DoesNotExist:
                create_data = {'name': name}
                if description is not None:
                    create_data['description'] = description
                if sortorder is not None:
                    create_data['sortorder'] = int(sortorder)
                Features.objects.create(**create_data)
                print(f"Row {i+1}: Feature {name} created")

def handle_category(row, i, action, df, sheet_name=""):
    """Handle Category records"""
    name = get_col(row, 'name', df)
    fullname = get_col(row, 'fullname', df)
    sortorder = get_col(row, 'sortorder', df)
    
    if action == 'delete':
        if fullname:
            try:
                Categories.objects.get(fullname=fullname).delete()
                print(f"Row {i+1}: Category {fullname} deleted")
            except Categories.DoesNotExist:
                print(f"Row {i+1}: Category not found")
    elif action == 'update':
        if fullname:
            try:
                cat = Categories.objects.get(fullname=fullname)
                if name is not None:
                    cat.name = name
                if sortorder is not None:
                    cat.sortorder = int(sortorder)
                cat.save()
                print(f"Row {i+1}: Category {fullname} updated")
            except Categories.DoesNotExist:
                print(f"Row {i+1}: Category not found")
    elif action == 'create':
        if fullname:
            try:
                Categories.objects.get(fullname=fullname)
                print(f"Row {i+1}: Category {fullname} already exists")
            except Categories.DoesNotExist:
                create_data = {'fullname': fullname}
                if name is not None:
                    create_data['name'] = name
                if sortorder is not None:
                    create_data['sortorder'] = int(sortorder)
                Categories.objects.create(**create_data)
                print(f"Row {i+1}: Category {fullname} created")

def handle_subcategory(row, i, action, df, sheet_name=""):
    """Handle Subcategory records"""
    name = get_col(row, 'name', df)
    fullname = get_col(row, 'fullname', df)
    sortorder = get_col(row, 'sortorder', df)
    category_fullname = get_col(row, 'categoryfullname', df)
    
    if action == 'delete':
        if fullname:
            try:
                Subcategories.objects.get(fullname=fullname).delete()
                print(f"Row {i+1}: Subcategory {fullname} deleted")
            except Subcategories.DoesNotExist:
                print(f"Row {i+1}: Subcategory not found")
    elif action == 'update':
        if fullname:
            try:
                subcat = Subcategories.objects.get(fullname=fullname)
                if name is not None:
                    subcat.name = name
                if sortorder is not None:
                    subcat.sortorder = int(sortorder)
                if category_fullname:
                    try:
                        cat = Categories.objects.get(fullname=category_fullname)
                        subcat.categories.add(cat)  # Add only, preserve existing
                    except Categories.DoesNotExist:
                        print(f"Row {i+1}: Category '{category_fullname}' not found")
                subcat.save()
                print(f"Row {i+1}: Subcategory {fullname} updated")
            except Subcategories.DoesNotExist:
                print(f"Row {i+1}: Subcategory not found")
    elif action == 'create':
        if fullname:
            try:
                Subcategories.objects.get(fullname=fullname)
                print(f"Row {i+1}: Subcategory {fullname} already exists")
            except Subcategories.DoesNotExist:
                create_data = {'fullname': fullname}
                if name is not None:
                    create_data['name'] = name
                if sortorder is not None:
                    create_data['sortorder'] = int(sortorder)
                subcat = Subcategories.objects.create(**create_data)
                if category_fullname:
                    try:
                        cat = Categories.objects.get(fullname=category_fullname)
                        subcat.categories.add(cat)
                    except Categories.DoesNotExist:
                        print(f"Row {i+1}: Category '{category_fullname}' not found")
                print(f"Row {i+1}: Subcategory {fullname} created")

def handle_itemtype(row, i, action, df, sheet_name=""):
    """Handle ItemType records"""
    name = get_col(row, 'name', df)
    fullname = get_col(row, 'fullname', df)
    sortorder = get_col(row, 'sortorder', df)
    category_fullname = get_col(row, 'categoryfullname', df)
    subcategory_fullname = get_col(row, 'subcategoryfullname', df)
    attribute_name = get_col(row, 'attribute', df)
    
    if action == 'delete':
        if fullname:
            try:
                ItemTypes.objects.get(fullname=fullname).delete()
                print(f"Row {i+1}: ItemType {fullname} deleted")
            except ItemTypes.DoesNotExist:
                print(f"Row {i+1}: ItemType not found")
    elif action == 'update':
        if fullname:
            try:
                itemtype = ItemTypes.objects.get(fullname=fullname)
                if name is not None:
                    itemtype.name = name
                if sortorder is not None:
                    itemtype.sortorder = int(sortorder)
                if category_fullname:
                    try:
                        itemtype.categories.add(Categories.objects.get(fullname=category_fullname))
                    except Categories.DoesNotExist:
                        print(f"Row {i+1}: Category '{category_fullname}' not found")
                if subcategory_fullname:
                    try:
                        itemtype.subcategories.add(Subcategories.objects.get(fullname=subcategory_fullname))
                    except Subcategories.DoesNotExist:
                        print(f"Row {i+1}: Subcategory '{subcategory_fullname}' not found")
                if attribute_name:
                    try:
                        itemtype.attributes.add(Attributes.objects.get(name=attribute_name))
                    except Attributes.DoesNotExist:
                        print(f"Row {i+1}: Attribute '{attribute_name}' not found")
                itemtype.save()
                print(f"Row {i+1}: ItemType {fullname} updated")
            except ItemTypes.DoesNotExist:
                print(f"Row {i+1}: ItemType not found")
    elif action == 'create':
        if fullname:
            try:
                ItemTypes.objects.get(fullname=fullname)
                print(f"Row {i+1}: ItemType {fullname} already exists")
            except ItemTypes.DoesNotExist:
                create_data = {'fullname': fullname}
                if name is not None:
                    create_data['name'] = name
                if sortorder is not None:
                    create_data['sortorder'] = int(sortorder)
                itemtype = ItemTypes.objects.create(**create_data)
                if category_fullname:
                    try:
                        itemtype.categories.add(Categories.objects.get(fullname=category_fullname))
                    except Categories.DoesNotExist:
                        print(f"Row {i+1}: Category '{category_fullname}' not found")
                if subcategory_fullname:
                    try:
                        itemtype.subcategories.add(Subcategories.objects.get(fullname=subcategory_fullname))
                    except Subcategories.DoesNotExist:
                        print(f"Row {i+1}: Subcategory '{subcategory_fullname}' not found")
                if attribute_name:
                    try:
                        itemtype.attributes.add(Attributes.objects.get(name=attribute_name))
                    except Attributes.DoesNotExist:
                        print(f"Row {i+1}: Attribute '{attribute_name}' not found")
                print(f"Row {i+1}: ItemType {fullname} created")

def handle_motortype(row, i, action, df, sheet_name=""):
    """Handle MotorType records"""
    name = get_col(row, 'name', df)
    sortorder = get_col(row, 'sortorder', df)
    
    if action == 'delete':
        if name:
            try:
                MotorTypes.objects.get(name=name).delete()
                print(f"Row {i+1}: MotorType {name} deleted")
            except MotorTypes.DoesNotExist:
                print(f"Row {i+1}: MotorType not found")
    elif action == 'update':
        if name:
            try:
                mt = MotorTypes.objects.get(name=name)
                if sortorder is not None:
                    mt.sortorder = int(sortorder)
                mt.save()
                print(f"Row {i+1}: MotorType {name} updated")
            except MotorTypes.DoesNotExist:
                print(f"Row {i+1}: MotorType not found")
    elif action == 'create':
        if name:
            try:
                MotorTypes.objects.get(name=name)
                print(f"Row {i+1}: MotorType {name} already exists")
            except MotorTypes.DoesNotExist:
                create_data = {'name': name}
                if sortorder is not None:
                    create_data['sortorder'] = int(sortorder)
                MotorTypes.objects.create(**create_data)
                print(f"Row {i+1}: MotorType {name} created")

def handle_listingtype(row, i, action, df, sheet_name=""):
    """Handle ListingType records"""
    name = get_col(row, 'name', df)
    retailer = get_col(row, 'retailer', df)
    
    if action == 'delete':
        if name:
            try:
                ListingTypes.objects.get(name=name).delete()
                print(f"Row {i+1}: ListingType {name} deleted")
            except ListingTypes.DoesNotExist:
                print(f"Row {i+1}: ListingType not found")
    elif action == 'update':
        if name:
            try:
                lt = ListingTypes.objects.get(name=name)
                if retailer:
                    try:
                        lt.retailer = Retailers.objects.get(name=retailer)
                    except Retailers.DoesNotExist:
                        print(f"Row {i+1}: Retailer '{retailer}' not found")
                elif retailer is None:
                    lt.retailer = None
                lt.save()
                print(f"Row {i+1}: ListingType {name} updated")
            except ListingTypes.DoesNotExist:
                print(f"Row {i+1}: ListingType not found")
    elif action == 'create':
        if name:
            try:
                ListingTypes.objects.get(name=name)
                print(f"Row {i+1}: ListingType {name} already exists")
            except ListingTypes.DoesNotExist:
                create_data = {'name': name}
                if retailer:
                    try:
                        create_data['retailer'] = Retailers.objects.get(name=retailer)
                    except Retailers.DoesNotExist:
                        print(f"Row {i+1}: Retailer '{retailer}' not found")
                ListingTypes.objects.create(**create_data)
                print(f"Row {i+1}: ListingType {name} created")

def handle_brand(row, i, action, df, sheet_name=""):
    """Handle Brand records"""
    name = get_col(row, 'name', df)
    color = get_col(row, 'color', df)
    logo = get_col(row, 'logo', df)
    sortorder = get_col(row, 'sortorder', df)
    
    if action == 'delete':
        if name:
            try:
                Brands.objects.get(name=name).delete()
                print(f"Row {i+1}: Brand {name} deleted")
            except Brands.DoesNotExist:
                print(f"Row {i+1}: Brand not found")
    elif action == 'update':
        if name:
            try:
                brand = Brands.objects.get(name=name)
                if color is not None:
                    brand.color = color
                if logo is not None:
                    brand.logo = logo
                if sortorder is not None:
                    brand.sortorder = int(sortorder)
                brand.save()
                print(f"Row {i+1}: Brand {name} updated")
            except Brands.DoesNotExist:
                print(f"Row {i+1}: Brand not found")
    elif action == 'create':
        if name:
            try:
                Brands.objects.get(name=name)
                print(f"Row {i+1}: Brand {name} already exists")
            except Brands.DoesNotExist:
                create_data = {'name': name}
                if color is not None:
                    create_data['color'] = color
                if logo is not None:
                    create_data['logo'] = logo
                if sortorder is not None:
                    create_data['sortorder'] = int(sortorder)
                Brands.objects.create(**create_data)
                print(f"Row {i+1}: Brand {name} created")

def handle_batteryvoltage(row, i, action, df, sheet_name=""):
    """Handle BatteryVoltage records"""
    value = get_col(row, 'value', df)
    
    if action == 'delete':
        if value is not None:
            try:
                BatteryVoltages.objects.get(value=int(value)).delete()
                print(f"Row {i+1}: BatteryVoltage {value} deleted")
            except BatteryVoltages.DoesNotExist:
                print(f"Row {i+1}: BatteryVoltage not found")
    elif action == 'update':
        if value is not None:
            try:
                BatteryVoltages.objects.get(value=int(value))
                print(f"Row {i+1}: BatteryVoltage {value} exists (no fields to update)")
            except BatteryVoltages.DoesNotExist:
                print(f"Row {i+1}: BatteryVoltage not found")
    elif action == 'create':
        if value is not None:
            try:
                BatteryVoltages.objects.get(value=int(value))
                print(f"Row {i+1}: BatteryVoltage {value} already exists")
            except BatteryVoltages.DoesNotExist:
                BatteryVoltages.objects.create(value=int(value))
                print(f"Row {i+1}: BatteryVoltage {value} created")

def handle_retailer(row, i, action, df, sheet_name=""):
    """Handle Retailer records"""
    name = get_col(row, 'name', df)
    url = get_col(row, 'url', df)
    logo = get_col(row, 'logo', df)
    sortorder = get_col(row, 'sortorder', df)
    
    if action == 'delete':
        if name:
            try:
                Retailers.objects.get(name=name).delete()
                print(f"Row {i+1}: Retailer {name} deleted")
            except Retailers.DoesNotExist:
                print(f"Row {i+1}: Retailer not found")
    elif action == 'update':
        if name:
            try:
                retailer = Retailers.objects.get(name=name)
                if url is not None:
                    retailer.url = url
                if logo is not None:
                    retailer.logo = logo
                if sortorder is not None:
                    retailer.sortorder = int(sortorder)
                retailer.save()
                print(f"Row {i+1}: Retailer {name} updated")
            except Retailers.DoesNotExist:
                print(f"Row {i+1}: Retailer not found")
    elif action == 'create':
        if name:
            try:
                Retailers.objects.get(name=name)
                print(f"Row {i+1}: Retailer {name} already exists")
            except Retailers.DoesNotExist:
                create_data = {'name': name}
                if url is not None:
                    create_data['url'] = url
                if logo is not None:
                    create_data['logo'] = logo
                if sortorder is not None:
                    create_data['sortorder'] = int(sortorder)
                Retailers.objects.create(**create_data)
                print(f"Row {i+1}: Retailer {name} created")

def handle_status(row, i, action, df, sheet_name=""):
    """Handle Status records"""
    name = get_col(row, 'name', df)
    color = get_col(row, 'color', df)
    icon = get_col(row, 'icon', df)
    sortorder = get_col(row, 'sortorder', df)
    
    if action == 'delete':
        if name:
            try:
                Statuses.objects.get(name=name).delete()
                print(f"Row {i+1}: Status {name} deleted")
            except Statuses.DoesNotExist:
                print(f"Row {i+1}: Status not found")
    elif action == 'update':
        if name:
            try:
                status = Statuses.objects.get(name=name)
                if color is not None:
                    status.color = color
                if icon is not None:
                    status.icon = icon
                if sortorder is not None:
                    status.sortorder = int(sortorder)
                status.save()
                print(f"Row {i+1}: Status {name} updated")
            except Statuses.DoesNotExist:
                print(f"Row {i+1}: Status not found")
    elif action == 'create':
        if name:
            try:
                Statuses.objects.get(name=name)
                print(f"Row {i+1}: Status {name} already exists")
            except Statuses.DoesNotExist:
                create_data = {'name': name}
                if color is not None:
                    create_data['color'] = color
                if icon is not None:
                    create_data['icon'] = icon
                if sortorder is not None:
                    create_data['sortorder'] = int(sortorder)
                Statuses.objects.create(**create_data)
                print(f"Row {i+1}: Status {name} created")

def handle_batteryplatform(row, i, action, df, sheet_name=""):
    """Handle BatteryPlatform records"""
    name = get_col(row, 'name', df)
    brand = get_col(row, 'brand', df)
    voltage_value = get_col(row, 'voltage', df)
    
    if action == 'delete':
        if name:
            try:
                BatteryPlatforms.objects.get(name=name).delete()
                print(f"Row {i+1}: BatteryPlatform {name} deleted")
            except BatteryPlatforms.DoesNotExist:
                print(f"Row {i+1}: BatteryPlatform not found")
    elif action == 'update':
        if name:
            try:
                bp = BatteryPlatforms.objects.get(name=name)
                if brand:
                    try:
                        bp.brand = Brands.objects.get(name=brand)
                    except Brands.DoesNotExist:
                        print(f"Row {i+1}: Brand '{brand}' not found")
                elif brand is None:
                    bp.brand = None
                if voltage_value is not None:
                    try:
                        voltage = BatteryVoltages.objects.get(value=int(voltage_value))
                        bp.voltage.add(voltage)  # Add only, preserve existing
                    except BatteryVoltages.DoesNotExist:
                        print(f"Row {i+1}: BatteryVoltage '{voltage_value}' not found")
                bp.save()
                print(f"Row {i+1}: BatteryPlatform {name} updated")
            except BatteryPlatforms.DoesNotExist:
                print(f"Row {i+1}: BatteryPlatform not found")
    elif action == 'create':
        if name:
            try:
                BatteryPlatforms.objects.get(name=name)
                print(f"Row {i+1}: BatteryPlatform {name} already exists")
            except BatteryPlatforms.DoesNotExist:
                create_data = {'name': name}
                if brand:
                    try:
                        create_data['brand'] = Brands.objects.get(name=brand)
                    except Brands.DoesNotExist:
                        print(f"Row {i+1}: Brand '{brand}' not found")
                bp = BatteryPlatforms.objects.create(**create_data)
                if voltage_value is not None:
                    try:
                        voltage = BatteryVoltages.objects.get(value=int(voltage_value))
                        bp.voltage.add(voltage)
                    except BatteryVoltages.DoesNotExist:
                        print(f"Row {i+1}: BatteryVoltage '{voltage_value}' not found")
                print(f"Row {i+1}: BatteryPlatform {name} created")

def handle_productline(row, i, action, df, sheet_name=""):
    """Handle ProductLine records"""
    name = get_col(row, 'name', df)
    brand = get_col(row, 'brand', df)
    description = get_col(row, 'description', df)
    image = get_col(row, 'image', df)
    batteryplatform_name = get_col(row, 'batteryplatform', df)
    batteryvoltage_value = get_col(row, 'batteryvoltage', df)
    
    if action == 'delete':
        if name and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                ProductLines.objects.get(name=name, brand=brand_obj).delete()
                print(f"Row {i+1}: ProductLine {name} deleted")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action == 'update':
        if name and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                pl = ProductLines.objects.get(name=name, brand=brand_obj)
                if description is not None:
                    pl.description = description
                if image is not None:
                    pl.image = image
                if batteryplatform_name:
                    try:
                        bp = BatteryPlatforms.objects.get(name=batteryplatform_name)
                        pl.batteryplatform.add(bp)  # Add only, preserve existing
                    except BatteryPlatforms.DoesNotExist:
                        print(f"Row {i+1}: BatteryPlatform '{batteryplatform_name}' not found")
                if batteryvoltage_value is not None:
                    try:
                        bv = BatteryVoltages.objects.get(value=int(batteryvoltage_value))
                        pl.batteryvoltage.add(bv)  # Add only, preserve existing
                    except BatteryVoltages.DoesNotExist:
                        print(f"Row {i+1}: BatteryVoltage '{batteryvoltage_value}' not found")
                pl.save()
                print(f"Row {i+1}: ProductLine {name} updated")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action == 'create':
        if name and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                try:
                    pl = ProductLines.objects.get(name=name, brand=brand_obj)
                    print(f"Row {i+1}: ProductLine {name} already exists, updating")
                    handle_productline(row, i, 'update', df, sheet_name)
                except ProductLines.DoesNotExist:
                    create_data = {'name': name, 'brand': brand_obj}
                    if description is not None:
                        create_data['description'] = description
                    if image is not None:
                        create_data['image'] = image
                    pl = ProductLines.objects.create(**create_data)
                    if batteryplatform_name:
                        try:
                            bp = BatteryPlatforms.objects.get(name=batteryplatform_name)
                            pl.batteryplatform.add(bp)
                        except BatteryPlatforms.DoesNotExist:
                            print(f"Row {i+1}: BatteryPlatform '{batteryplatform_name}' not found")
                    if batteryvoltage_value is not None:
                        try:
                            bv = BatteryVoltages.objects.get(value=int(batteryvoltage_value))
                            pl.batteryvoltage.add(bv)
                        except BatteryVoltages.DoesNotExist:
                            print(f"Row {i+1}: BatteryVoltage '{batteryvoltage_value}' not found")
                    print(f"Row {i+1}: ProductLine {name} created")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")

def handle_pricelisting(row, i, action, df, sheet_name=""):
    """Handle PriceListing records"""
    brand_name = get_col(row, 'brand', df)
    product_sku = get_col(row, 'product_sku', df)
    retailer_name = get_col(row, 'retailer', df)
    retailer_sku = get_col(row, 'retailer_sku', df)
    price = get_col(row, 'price', df)
    currency = get_col(row, 'currency', df)
    url = get_col(row, 'url', df)
    datepulled = get_col(row, 'datepulled', df)
    
    if action == 'delete':
        if brand_name and product_sku and retailer_name:
            try:
                brand_obj = Brands.objects.get(name=brand_name)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                retailer = Retailers.objects.get(name=retailer_name)
                
                query = {'retailer': retailer, 'product': product}
                if retailer_sku is not None:
                    query['retailer_sku'] = retailer_sku
                if price is not None:
                    query['price'] = float(price)
                if datepulled is not None:
                    query['datepulled'] = pd.to_datetime(datepulled).date() if isinstance(datepulled, str) else datepulled
                
                try:
                    PriceListings.objects.get(**query).delete()
                    print(f"Row {i+1}: PriceListing deleted")
                except PriceListings.DoesNotExist:
                    print(f"Row {i+1}: PriceListing not found")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")
    elif action in ['update', 'create']:
        if brand_name and product_sku and retailer_name and price is not None:
            try:
                brand_obj = Brands.objects.get(name=brand_name)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                retailer = Retailers.objects.get(name=retailer_name)
                
                create_data = {
                    'retailer': retailer,
                    'product': product,
                    'price': float(price)
                }
                if retailer_sku is not None:
                    create_data['retailer_sku'] = retailer_sku
                if currency is not None:
                    create_data['currency'] = currency
                else:
                    create_data['currency'] = 'USD'
                if url is not None:
                    create_data['url'] = url
                if datepulled is not None:
                    create_data['datepulled'] = pd.to_datetime(datepulled).date() if isinstance(datepulled, str) else datepulled
                else:
                    create_data['datepulled'] = date.today()
                
                query = {
                    'retailer': retailer,
                    'product': product,
                    'price': create_data['price'],
                    'datepulled': create_data['datepulled']
                }
                if retailer_sku is not None:
                    query['retailer_sku'] = retailer_sku
                
                try:
                    pl = PriceListings.objects.get(**query)
                    if currency is not None:
                        pl.currency = currency
                    if url is not None:
                        pl.url = url
                    pl.save()
                    print(f"Row {i+1}: PriceListing updated")
                except PriceListings.DoesNotExist:
                    PriceListings.objects.create(**create_data)
                    print(f"Row {i+1}: PriceListing created")
            except Exception as e:
                print(f"Row {i+1}: {type(e).__name__}: {str(e)}")

# ============================================================================
# Routing dictionary
# ============================================================================

ROUTERS = {
    'product': handle_product,
    'component': handle_component,
    'componentfeature': handle_componentfeature,
    'componentattribute': handle_componentattribute,
    'productcomponent': handle_productcomponent,
    'productaccessory': handle_productaccessory,
    'productspecification': handle_productspecification,
    'productimage': handle_productimage,
    'attribute': handle_attribute,
    'feature': handle_feature,
    'category': handle_category,
    'subcategory': handle_subcategory,
    'itemtype': handle_itemtype,
    'motortype': handle_motortype,
    'listingtype': handle_listingtype,
    'brand': handle_brand,
    'batteryvoltage': handle_batteryvoltage,
    'retailer': handle_retailer,
    'status': handle_status,
    'batteryplatform': handle_batteryplatform,
    'productline': handle_productline,
    'pricelisting': handle_pricelisting,
}

# ============================================================================
# Function to process a single sheet
# ============================================================================

def process_sheet(file_path, sheet_name, excel_file):
    """Process a single sheet from the Excel file"""
    print(f"\n{'='*60}")
    print(f"Processing sheet: {sheet_name}")
    print(f"{'='*60}")
    
    try:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        print(f"Loaded {len(df)} rows and {len(df.columns)} columns")
        
        if len(df) == 0:
            print(f"Sheet '{sheet_name}' is empty, skipping")
            return
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            if 'action' not in df.columns:
                print(f"Sheet '{sheet_name}', Row {i+1}: Skipping - 'action' column not found")
                continue
            
            if 'recordtype' not in df.columns:
                print(f"Sheet '{sheet_name}', Row {i+1}: Skipping - 'recordtype' column not found")
                continue
            
            action = get_col(row, 'action', df)
            recordtype = get_col(row, 'recordtype', df)
            
            if not action:
                continue
            
            if not recordtype:
                print(f"Sheet '{sheet_name}', Row {i+1}: Skipping - recordtype is empty")
                continue
            
            recordtype_lower = str(recordtype).lower().strip()
            
            if recordtype_lower in ROUTERS:
                try:
                    ROUTERS[recordtype_lower](row, i, action, df, sheet_name)
                except Exception as e:
                    print(f"Sheet '{sheet_name}', Row {i+1}: Error processing {recordtype_lower}: {type(e).__name__}: {str(e)}")
            else:
                print(f"Sheet '{sheet_name}', Row {i+1}: Unknown recordtype '{recordtype}', skipping")
        
        print(f"\nCompleted processing sheet: {sheet_name}")
        
    except Exception as e:
        print(f"Error processing sheet '{sheet_name}': {type(e).__name__}: {str(e)}")

# ============================================================================
# Main processing loop - process all selected sheets
# ============================================================================

print(f"\nStarting import of {len(selected_sheets)} sheet(s)...")

total_sheets = len(selected_sheets)
for sheet_idx, sheet_name in enumerate(selected_sheets, 1):
    print(f"\n[{sheet_idx}/{total_sheets}] Processing sheet: {sheet_name}")
    process_sheet(file_path, sheet_name, excel_file)

print(f"\n{'='*60}")
print(f"Import complete! Processed {len(selected_sheets)} sheet(s)")
print(f"{'='*60}")

