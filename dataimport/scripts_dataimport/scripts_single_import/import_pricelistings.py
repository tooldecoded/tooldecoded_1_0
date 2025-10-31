import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()
from pathlib import Path
from toolanalysis.models import PriceListings, Retailers, Products, Brands
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
        # Product identification: brand + sku
        brand_name = get_col(row, 'brand')
        product_sku = get_col(row, 'product_sku')
        # Retailer identification: name
        retailer_name = get_col(row, 'retailer')
        retailer_sku = get_col(row, 'retailer_sku')
        price = get_col(row, 'price')
        currency = get_col(row, 'currency')
        url = get_col(row, 'url')
        datepulled = get_col(row, 'datepulled')
        
        if action == 'delete':
            if brand_name and product_sku and retailer_name:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    product = Products.objects.get(sku=product_sku, brand=brand_obj)
                    retailer = Retailers.objects.get(name=retailer_name)
                    
                    # PriceListings unique_together is (retailer, product, retailer_sku, price, datepulled)
                    # Need all fields for exact match
                    query = {
                        'retailer': retailer,
                        'product': product
                    }
                    if retailer_sku is not None:
                        query['retailer_sku'] = retailer_sku
                    if price is not None:
                        try:
                            query['price'] = float(price)
                        except (ValueError, TypeError):
                            print(f"Row {i+1}: Invalid price '{price}', skipping")
                            continue
                    if datepulled is not None:
                        query['datepulled'] = pd.to_datetime(datepulled).date() if isinstance(datepulled, str) else datepulled
                    
                    try:
                        pricelisting = PriceListings.objects.get(**query)
                        pricelisting.delete()
                        print(f"PriceListing deleted for product {product.name}, retailer {retailer.name}")
                    except PriceListings.DoesNotExist:
                        print(f"Row {i+1}: PriceListing not found")
                    except PriceListings.MultipleObjectsReturned:
                        print(f"Row {i+1}: Multiple PriceListings found, cannot delete without all identifying fields")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found")
                except Products.DoesNotExist:
                    print(f"Row {i+1}: Product with SKU '{product_sku}' and brand '{brand_name}' not found")
                except Retailers.DoesNotExist:
                    print(f"Row {i+1}: Retailer '{retailer_name}' not found")
            else:
                print(f"Row {i+1}: Skipping delete - missing required fields")
        elif action == 'update':
            if brand_name and product_sku and retailer_name and price is not None:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    product = Products.objects.get(sku=product_sku, brand=brand_obj)
                    retailer = Retailers.objects.get(name=retailer_name)
                    
                    # Find existing PriceListing (need all unique fields for exact match)
                    query = {
                        'retailer': retailer,
                        'product': product,
                        'price': float(price)
                    }
                    if retailer_sku is not None:
                        query['retailer_sku'] = retailer_sku
                    else:
                        query['retailer_sku__isnull'] = True
                    if datepulled is not None:
                        query['datepulled'] = pd.to_datetime(datepulled).date() if isinstance(datepulled, str) else datepulled
                    else:
                        # If datepulled not provided, we can't uniquely identify
                        print(f"Row {i+1}: Warning - datepulled not provided, cannot uniquely identify PriceListing to update. Skipping.")
                        continue
                    
                    try:
                        pricelisting = PriceListings.objects.get(**query)
                        # Update fields
                        if currency is not None:
                            pricelisting.currency = currency
                        if url is not None:
                            pricelisting.url = url
                        pricelisting.save()
                        print(f"PriceListing updated for product {product.name}, retailer {retailer.name}")
                    except PriceListings.DoesNotExist:
                        # Doesn't exist, create it
                        create_data = {
                            'retailer': retailer,
                            'product': product,
                            'price': float(price)
                        }
                        if retailer_sku is not None:
                            create_data['retailer_sku'] = retailer_sku
                        if currency is not None:
                            create_data['currency'] = currency
                        if url is not None:
                            create_data['url'] = url
                        if datepulled is not None:
                            create_data['datepulled'] = pd.to_datetime(datepulled).date() if isinstance(datepulled, str) else datepulled
                        PriceListings.objects.create(**create_data)
                        print(f"PriceListing created (was update action, but didn't exist) for product {product.name}, retailer {retailer.name}")
                    except PriceListings.MultipleObjectsReturned:
                        print(f"Row {i+1}: Multiple PriceListings found (this shouldn't happen with unique_together). Skipping.")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found, skipping")
                except Products.DoesNotExist:
                    print(f"Row {i+1}: Product with SKU '{product_sku}' and brand '{brand_name}' not found, skipping")
                except Retailers.DoesNotExist:
                    print(f"Row {i+1}: Retailer '{retailer_name}' not found, skipping")
                except (ValueError, TypeError) as e:
                    print(f"Row {i+1}: Invalid price value: {str(e)}")
            else:
                print(f"Row {i+1}: Skipping update - missing required fields")
        elif action == 'create':
            if brand_name and product_sku and retailer_name and price is not None:
                try:
                    brand_obj = Brands.objects.get(name=brand_name)
                    product = Products.objects.get(sku=product_sku, brand=brand_obj)
                    retailer = Retailers.objects.get(name=retailer_name)
                    
                    # Build create data
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
                        create_data['currency'] = 'USD'  # Default
                    if url is not None:
                        create_data['url'] = url
                    if datepulled is not None:
                        create_data['datepulled'] = pd.to_datetime(datepulled).date() if isinstance(datepulled, str) else datepulled
                    
                    # Check if it already exists (by unique_together)
                    query = {
                        'retailer': retailer,
                        'product': product,
                        'price': create_data['price']
                    }
                    if retailer_sku is not None:
                        query['retailer_sku'] = retailer_sku
                    else:
                        query['retailer_sku__isnull'] = True
                    if datepulled is not None:
                        query['datepulled'] = create_data.get('datepulled')
                    else:
                        # Default to today if not provided
                        from datetime import date
                        query['datepulled'] = date.today()
                        create_data['datepulled'] = date.today()
                    
                    try:
                        # PriceListing exists, don't create duplicate
                        pricelisting = PriceListings.objects.get(**query)
                        print(f"PriceListing already exists for product {product.name}, retailer {retailer.name}, skipping create")
                    except PriceListings.DoesNotExist:
                        # PriceListing doesn't exist, create it
                        PriceListings.objects.create(**create_data)
                        print(f"PriceListing created for product {product.name}, retailer {retailer.name}")
                    except PriceListings.MultipleObjectsReturned:
                        print(f"Row {i+1}: Multiple PriceListings found (this shouldn't happen with unique_together). Skipping.")
                except Brands.DoesNotExist:
                    print(f"Row {i+1}: Brand '{brand_name}' not found, skipping create")
                except Products.DoesNotExist:
                    print(f"Row {i+1}: Product with SKU '{product_sku}' and brand '{brand_name}' not found, skipping create")
                except Retailers.DoesNotExist:
                    print(f"Row {i+1}: Retailer '{retailer_name}' not found, skipping create")
                except (ValueError, TypeError) as e:
                    print(f"Row {i+1}: Invalid price value: {str(e)}")
            else:
                print(f"Row {i+1}: Skipping create - missing required fields")
        else:
            print(f"Row {i+1}: Unknown action '{action}', skipping")

