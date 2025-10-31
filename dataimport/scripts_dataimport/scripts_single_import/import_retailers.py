import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()
from pathlib import Path
from toolanalysis.models import Retailers
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
        name = get_col(row, 'name')
        url = get_col(row, 'url')
        logo = get_col(row, 'logo')
        sortorder = get_col(row, 'sortorder')
        
        if action == 'delete':
            if name:
                try:
                    retailer = Retailers.objects.get(name=name)
                    retailer.delete()
                    print(f"Retailer {name} deleted")
                except Retailers.DoesNotExist:
                    print(f"Row {i+1}: Retailer '{name}' not found")
            else:
                print(f"Row {i+1}: Skipping delete - missing required field (name)")
        elif action == 'update':
            if name:
                try:
                    retailer = Retailers.objects.get(name=name)
                    
                    # Update fields
                    if url is not None:
                        retailer.url = url
                    if logo is not None:
                        retailer.logo = logo
                    if sortorder is not None:
                        try:
                            retailer.sortorder = int(sortorder)
                        except (ValueError, TypeError):
                            print(f"Row {i+1}: Invalid sortorder '{sortorder}', skipping")
                    # Note: name is unique, so can't change it in update
                    
                    retailer.save()
                    print(f"Retailer {name} updated")
                except Retailers.DoesNotExist:
                    print(f"Row {i+1}: Retailer '{name}' not found for update")
            else:
                print(f"Row {i+1}: Skipping update - missing required field (name)")
        elif action == 'create':
            if name:
                try:
                    # Check if exists
                    retailer = Retailers.objects.get(name=name)
                    print(f"Retailer {name} already exists, skipping create")
                except Retailers.DoesNotExist:
                    # Create it
                    create_data = {'name': name}
                    if url is not None:
                        create_data['url'] = url
                    if logo is not None:
                        create_data['logo'] = logo
                    if sortorder is not None:
                        try:
                            create_data['sortorder'] = int(sortorder)
                        except (ValueError, TypeError):
                            print(f"Row {i+1}: Invalid sortorder '{sortorder}', skipping")
                    Retailers.objects.create(**create_data)
                    print(f"Retailer {name} created")
            else:
                print(f"Row {i+1}: Skipping create - missing required field (name)")
        else:
            print(f"Row {i+1}: Unknown action '{action}', skipping")

