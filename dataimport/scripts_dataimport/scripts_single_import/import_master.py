import os
import django
import sys
import io
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
from tkinter import scrolledtext, ttk
from datetime import date
from collections import defaultdict
from contextlib import redirect_stdout

# ============================================================================
# Custom output capture for detailed logging
# ============================================================================

class OutputCapture:
    """Capture stdout while still printing to console and collecting messages"""
    def __init__(self, original_stdout, results_collector=None):
        self.original_stdout = original_stdout
        self.results_collector = results_collector
        self.buffer = []
        self.line_buffer = ""
        
    def write(self, text):
        """Write to both console and buffer"""
        # Always write to console
        self.original_stdout.write(text)
        
        # Accumulate text until we have a complete line
        self.line_buffer += text
        if '\n' in text:
            lines = self.line_buffer.split('\n')
            # Process complete lines, keep incomplete line in buffer
            for line in lines[:-1]:
                line = line.strip()
                if line:
                    self.buffer.append(line)
                    # Extract meaningful operation messages for results
                    if self.results_collector and line:
                        # Look for operation messages (Row X: ... created/updated/deleted/etc.)
                        # Capture all database operation messages that start with "Row"
                        keywords = ['created', 'updated', 'deleted', 'purged', 'already exists']
                        line_lower = line.lower().strip()
                        # Capture any line that starts with "Row" and contains an operation keyword
                        # This captures ALL record types: products, components, attributes, features,
                        # categories, brands, retailers, statuses, battery platforms, etc.
                        if line_lower.startswith('row') and any(keyword in line_lower for keyword in keywords):
                            # Prevent duplicates and ensure we capture all operations
                            if len(self.results_collector['details']) < 1000:
                                # Use original line (not lowercased) for display
                                if line not in self.results_collector['details']:
                                    self.results_collector['details'].append(line)
            # Keep the last incomplete line in buffer
            self.line_buffer = lines[-1]
        return len(text)
    
    def flush(self):
        """Flush the original stdout and process any remaining buffer content"""
        self.original_stdout.flush()
        # Process any remaining buffer content (important for last line without newline)
        if self.line_buffer:
            line = self.line_buffer.strip()
            if line:  # Only process non-empty lines
                self.buffer.append(line)
                if self.results_collector:
                    # Capture all database operation messages that start with "Row"
                    keywords = ['created', 'updated', 'deleted', 'purged', 'already exists']
                    line_lower = line.lower().strip()
                    # Capture any line that starts with "Row" and contains an operation keyword
                    if line_lower.startswith('row') and any(keyword in line_lower for keyword in keywords):
                        # Prevent duplicates and ensure we capture all operations
                        if len(self.results_collector['details']) < 1000:
                            if line not in self.results_collector['details']:
                                self.results_collector['details'].append(line)
            self.line_buffer = ""
    
    def get_output(self):
        """Get captured output"""
        return '\n'.join(self.buffer)

# ============================================================================
# Column requirements mapping (defined early for UI use)
# ============================================================================

COLUMNS_MAP = {
    'product': {
        'required': ['action', 'recordtype', 'brand', 'product_sku'],
        'optional': ['name', 'description', 'image', 'listingtype', 'status', 
                    'motortype', 'releasedate', 'discontinueddate', 'isaccessory',
                    'itemtypefullname', 'subcategoryfullname', 'categoryfullname',
                    'batteryplatform', 'batteryvoltage', 'features'],
        'description': 'Products - Main product records'
    },
    'component': {
        'required': ['action', 'recordtype', 'brand', 'component_sku'],
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
        'optional': ['unit', 'description', 'sortorder', 'displayformat'],
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
    
    def on_exit():
        """Properly exit the application"""
        try:
            help_dialog.grab_release()
            help_dialog.destroy()
        except:
            pass
        sys.exit(0)
    
    close_button = tk.Button(button_frame, text="Close and Continue", command=lambda: help_dialog.destroy(), width=20)
    close_button.pack(side=tk.LEFT, padx=5)
    
    exit_button = tk.Button(button_frame, text="Exit Application", command=on_exit, width=20)
    exit_button.pack(side=tk.LEFT, padx=5)
    
    # Set up window close protocol
    def on_close():
        """Handle window close (X button) - just close, don't exit"""
        try:
            help_dialog.grab_release()
            help_dialog.destroy()
        except:
            pass
    
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

def analyze_sheets(file_path, sheet_names):
    """
    Analyze selected sheets and create a summary of what will be processed.
    Returns a dictionary with summary information.
    """
    summary = {
        'total_rows': 0,
        'by_sheet': {},
        'by_action': defaultdict(int),
        'by_recordtype': defaultdict(int),
        'by_sheet_action': defaultdict(lambda: defaultdict(int)),
        'by_sheet_recordtype': defaultdict(lambda: defaultdict(int)),
        'errors': []
    }
    
    try:
        excel_file = pd.ExcelFile(file_path)
        
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheet_summary = {
                    'total_rows': len(df),
                    'valid_rows': 0,
                    'invalid_rows': 0,
                    'by_action': defaultdict(int),
                    'by_recordtype': defaultdict(int)
                }
                
                if len(df) == 0:
                    summary['by_sheet'][sheet_name] = sheet_summary
                    continue
                
                if 'action' not in df.columns or 'recordtype' not in df.columns:
                    summary['errors'].append(f"Sheet '{sheet_name}': Missing 'action' or 'recordtype' column")
                    summary['by_sheet'][sheet_name] = sheet_summary
                    continue
                
                for i in range(len(df)):
                    row = df.iloc[i]
                    action = get_col(row, 'action', df)
                    recordtype = get_col(row, 'recordtype', df)
                    
                    if action and recordtype:
                        action_lower = str(action).lower().strip()
                        recordtype_lower = str(recordtype).lower().strip()
                        
                        sheet_summary['valid_rows'] += 1
                        sheet_summary['by_action'][action_lower] += 1
                        sheet_summary['by_recordtype'][recordtype_lower] += 1
                        summary['by_action'][action_lower] += 1
                        summary['by_recordtype'][recordtype_lower] += 1
                        summary['by_sheet_action'][sheet_name][action_lower] += 1
                        summary['by_sheet_recordtype'][sheet_name][recordtype_lower] += 1
                        summary['total_rows'] += 1
                    else:
                        sheet_summary['invalid_rows'] += 1
                
                summary['by_sheet'][sheet_name] = sheet_summary
                
            except Exception as e:
                summary['errors'].append(f"Sheet '{sheet_name}': {str(e)}")
    
    except Exception as e:
        summary['errors'].append(f"Error analyzing sheets: {str(e)}")
    
    return summary

def show_preview_dialog(parent_window, summary):
    """
    Show a dialog with a preview/summary of what will be processed.
    Returns True if user confirms, False if cancelled.
    """
    parent_window.withdraw()
    parent_window.update_idletasks()
    
    preview_dialog = tk.Toplevel(parent_window)
    preview_dialog.title("Import Preview - Review Before Processing")
    preview_dialog.geometry("800x700")
    
    # Center the dialog
    preview_dialog.update_idletasks()
    x = (preview_dialog.winfo_screenwidth() // 2) - (preview_dialog.winfo_width() // 2)
    y = (preview_dialog.winfo_screenheight() // 2) - (preview_dialog.winfo_height() // 2)
    preview_dialog.geometry(f"+{x}+{y}")
    
    # Create main frame
    main_frame = tk.Frame(preview_dialog)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Title
    title_label = tk.Label(main_frame, text="Import Preview", font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 10))
    
    # Summary text area
    text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=("Courier", 9), width=80, height=30)
    text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    
    # Build summary text
    summary_text = []
    summary_text.append("=" * 70)
    summary_text.append("IMPORT PREVIEW SUMMARY")
    summary_text.append("=" * 70)
    summary_text.append("")
    
    summary_text.append(f"Total Sheets: {len(summary['by_sheet'])}")
    summary_text.append(f"Total Valid Rows: {summary['total_rows']}")
    summary_text.append("")
    
    if summary['errors']:
        summary_text.append("WARNINGS/ERRORS:")
        summary_text.append("-" * 70)
        for error in summary['errors']:
            summary_text.append(f"  ⚠ {error}")
        summary_text.append("")
    
    summary_text.append("BREAKDOWN BY ACTION:")
    summary_text.append("-" * 70)
    for action in sorted(summary['by_action'].keys()):
        count = summary['by_action'][action]
        summary_text.append(f"  {action.upper():<15} {count:>5} row(s)")
    summary_text.append("")
    
    summary_text.append("BREAKDOWN BY RECORD TYPE:")
    summary_text.append("-" * 70)
    for recordtype in sorted(summary['by_recordtype'].keys()):
        count = summary['by_recordtype'][recordtype]
        summary_text.append(f"  {recordtype:<20} {count:>5} row(s)")
    summary_text.append("")
    
    summary_text.append("DETAILED BREAKDOWN BY SHEET:")
    summary_text.append("=" * 70)
    for sheet_name in sorted(summary['by_sheet'].keys()):
        sheet_info = summary['by_sheet'][sheet_name]
        summary_text.append("")
        summary_text.append(f"Sheet: {sheet_name}")
        summary_text.append("-" * 70)
        summary_text.append(f"  Total Rows: {sheet_info['total_rows']}")
        summary_text.append(f"  Valid Rows: {sheet_info['valid_rows']}")
        summary_text.append(f"  Invalid Rows: {sheet_info['invalid_rows']}")
        
        if sheet_info['by_action']:
            summary_text.append("  Actions:")
            for action, count in sorted(sheet_info['by_action'].items()):
                summary_text.append(f"    {action.upper():<15} {count:>5}")
        
        if sheet_info['by_recordtype']:
            summary_text.append("  Record Types:")
            for rt, count in sorted(sheet_info['by_recordtype'].items()):
                summary_text.append(f"    {rt:<20} {count:>5}")
    
    text_area.insert(1.0, "\n".join(summary_text))
    text_area.config(state=tk.DISABLED)
    
    # Buttons
    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=10)
    
    confirmed = [False]
    
    def on_confirm():
        confirmed[0] = True
        preview_dialog.destroy()
    
    def on_cancel():
        confirmed[0] = False
        preview_dialog.destroy()
    
    confirm_button = tk.Button(button_frame, text="Confirm and Process", command=on_confirm, width=20, bg="#4CAF50", fg="white")
    confirm_button.pack(side=tk.LEFT, padx=5)
    
    cancel_button = tk.Button(button_frame, text="Cancel", command=on_cancel, width=20)
    cancel_button.pack(side=tk.LEFT, padx=5)
    
    preview_dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    
    preview_dialog.update_idletasks()
    preview_dialog.lift()
    preview_dialog.focus_force()
    preview_dialog.grab_set()
    preview_dialog.wait_window()
    
    try:
        parent_window.deiconify()
        parent_window.update_idletasks()
    except:
        pass
    
    return confirmed[0]

def show_results_dialog(parent_window, results):
    """
    Show a dialog with detailed results of the import process.
    """
    parent_window.withdraw()
    parent_window.update_idletasks()
    
    results_dialog = tk.Toplevel(parent_window)
    results_dialog.title("Import Results - Detailed Report")
    results_dialog.geometry("900x750")
    
    # Center the dialog
    results_dialog.update_idletasks()
    x = (results_dialog.winfo_screenwidth() // 2) - (results_dialog.winfo_width() // 2)
    y = (results_dialog.winfo_screenheight() // 2) - (results_dialog.winfo_height() // 2)
    results_dialog.geometry(f"+{x}+{y}")
    
    # Create main frame with notebook for tabs
    main_frame = tk.Frame(results_dialog)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Title
    title_label = tk.Label(main_frame, text="Import Results", font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 10))
    
    # Create notebook for tabs
    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    
    # Summary tab
    summary_frame = tk.Frame(notebook)
    notebook.add(summary_frame, text="Summary")
    
    summary_text = scrolledtext.ScrolledText(summary_frame, wrap=tk.WORD, font=("Courier", 9), width=80, height=30)
    summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    summary_lines = []
    summary_lines.append("=" * 70)
    summary_lines.append("IMPORT RESULTS SUMMARY")
    summary_lines.append("=" * 70)
    summary_lines.append("")
    summary_lines.append(f"Total Sheets Processed: {results['total_sheets']}")
    summary_lines.append(f"Total Rows Processed: {results['total_rows']}")
    summary_lines.append(f"Successfully Processed: {results['success_count']}")
    summary_lines.append(f"Errors: {results['error_count']}")
    summary_lines.append(f"Warnings: {results['warning_count']}")
    summary_lines.append("")
    
    if results['by_action']:
        summary_lines.append("RESULTS BY ACTION:")
        summary_lines.append("-" * 70)
        for action in sorted(results['by_action'].keys()):
            count = results['by_action'][action]
            summary_lines.append(f"  {action.upper():<15} {count:>5}")
        summary_lines.append("")
    
    if results['by_recordtype']:
        summary_lines.append("RESULTS BY RECORD TYPE:")
        summary_lines.append("-" * 70)
        for rt in sorted(results['by_recordtype'].keys()):
            count = results['by_recordtype'][rt]
            summary_lines.append(f"  {rt:<20} {count:>5}")
        summary_lines.append("")
    
    # Add detailed operation records below the summary
    if results['details']:
        summary_lines.append("")
        summary_lines.append("=" * 70)
        summary_lines.append("DETAILED OPERATION RECORDS")
        summary_lines.append("=" * 70)
        summary_lines.append("")
        summary_lines.append("This section shows each database operation that was performed:")
        summary_lines.append("")
        if len(results['details']) >= 1000:
            summary_lines.append("NOTE: Detailed log is limited to first 1000 entries for performance.")
            summary_lines.append("Check console output for complete log.")
            summary_lines.append("")
        summary_lines.append("-" * 70)
        summary_lines.append("")
        
        # Group details by operation type for better readability
        created_ops = []
        updated_ops = []
        deleted_ops = []
        purged_ops = []
        other_ops = []
        
        for detail in results['details']:
            detail_lower = detail.lower()
            if 'created' in detail_lower or 'already exists' in detail_lower:
                created_ops.append(detail)
            elif 'updated' in detail_lower:
                updated_ops.append(detail)
            elif 'deleted' in detail_lower:
                deleted_ops.append(detail)
            elif 'purged' in detail_lower:
                purged_ops.append(detail)
            else:
                other_ops.append(detail)
        
        # Display grouped operations
        if created_ops:
            summary_lines.append(f"CREATED OPERATIONS ({len(created_ops)}):")
            summary_lines.append("-" * 70)
            for op in created_ops:
                summary_lines.append(f"  {op}")
            summary_lines.append("")
        
        if updated_ops:
            summary_lines.append(f"UPDATED OPERATIONS ({len(updated_ops)}):")
            summary_lines.append("-" * 70)
            for op in updated_ops:
                summary_lines.append(f"  {op}")
            summary_lines.append("")
        
        if deleted_ops:
            summary_lines.append(f"DELETED OPERATIONS ({len(deleted_ops)}):")
            summary_lines.append("-" * 70)
            for op in deleted_ops:
                summary_lines.append(f"  {op}")
            summary_lines.append("")
        
        if purged_ops:
            summary_lines.append(f"PURGED OPERATIONS ({len(purged_ops)}):")
            summary_lines.append("-" * 70)
            for op in purged_ops:
                summary_lines.append(f"  {op}")
            summary_lines.append("")
        
        if other_ops:
            summary_lines.append(f"OTHER OPERATIONS ({len(other_ops)}):")
            summary_lines.append("-" * 70)
            for op in other_ops:
                summary_lines.append(f"  {op}")
            summary_lines.append("")
    
    summary_text.insert(1.0, "\n".join(summary_lines))
    summary_text.config(state=tk.DISABLED)
    
    # Errors tab
    errors_frame = tk.Frame(notebook)
    notebook.add(errors_frame, text=f"Errors ({results['error_count']})")
    
    errors_text = scrolledtext.ScrolledText(errors_frame, wrap=tk.WORD, font=("Courier", 9), width=80, height=30)
    errors_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    if results['errors']:
        errors_lines = []
        errors_lines.append("=" * 70)
        errors_lines.append("ERROR DETAILS")
        errors_lines.append("=" * 70)
        errors_lines.append("")
        for i, error in enumerate(results['errors'], 1):
            errors_lines.append(f"{i}. {error}")
        errors_text.insert(1.0, "\n".join(errors_lines))
    else:
        errors_text.insert(1.0, "No errors occurred during import.")
    
    errors_text.config(state=tk.DISABLED)
    
    # Warnings tab
    warnings_frame = tk.Frame(notebook)
    notebook.add(warnings_frame, text=f"Warnings ({results['warning_count']})")
    
    warnings_text = scrolledtext.ScrolledText(warnings_frame, wrap=tk.WORD, font=("Courier", 9), width=80, height=30)
    warnings_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    if results['warnings']:
        warnings_lines = []
        warnings_lines.append("=" * 70)
        warnings_lines.append("WARNING DETAILS")
        warnings_lines.append("=" * 70)
        warnings_lines.append("")
        for i, warning in enumerate(results['warnings'], 1):
            warnings_lines.append(f"{i}. {warning}")
        warnings_text.insert(1.0, "\n".join(warnings_lines))
    else:
        warnings_text.insert(1.0, "No warnings occurred during import.")
    
    warnings_text.config(state=tk.DISABLED)
    
    # Close button
    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=10)
    
    close_button = tk.Button(button_frame, text="Close", command=results_dialog.destroy, width=20)
    close_button.pack()
    
    results_dialog.protocol("WM_DELETE_WINDOW", results_dialog.destroy)
    
    results_dialog.update_idletasks()
    results_dialog.lift()
    results_dialog.focus_force()
    results_dialog.grab_set()
    results_dialog.wait_window()
    
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
        ['action', 'recordtype', 'brand', 'product_sku']
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
    product_sku = get_col(row, 'product_sku', df)
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
        if product_sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                product.delete()
                print(f"Row {i+1}: Product {product.name} deleted")
            except Brands.DoesNotExist:
                print(f"Row {i+1}: Brand '{brand}' not found")
            except Products.DoesNotExist:
                print(f"Row {i+1}: Product not found")
    elif action == 'update':
        if product_sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                
                updated_fields = []
                m2m_added = []
                
                if name is not None:
                    old_name = product.name
                    product.name = name
                    if old_name != name:
                        updated_fields.append(f"name='{name}'")
                if description is not None:
                    old_desc = product.description
                    product.description = description
                    if old_desc != description:
                        desc_str = f"{description[:50]}..." if description and len(str(description)) > 50 else str(description)
                        updated_fields.append(f"description='{desc_str}'")
                if image is not None:
                    old_img = product.image
                    product.image = image
                    if old_img != image:
                        updated_fields.append(f"image='{image}'")
                if listingtype:
                    try:
                        old_lt = product.listingtype.name if product.listingtype else None
                        product.listingtype = ListingTypes.objects.get(name=listingtype)
                        if old_lt != listingtype:
                            updated_fields.append(f"listingtype='{listingtype}'")
                    except ListingTypes.DoesNotExist:
                        print(f"Row {i+1}: ListingType '{listingtype}' not found, skipping")
                if status:
                    try:
                        status_obj = Statuses.objects.get(name=str(status).strip())
                        old_status = product.status.name if product.status else None
                        product.status = status_obj
                        if old_status != status_obj.name:
                            updated_fields.append(f"status='{status_obj.name}'")
                    except Statuses.DoesNotExist:
                        print(f"Row {i+1}: Status '{status}' not found, skipping")
                    except Exception as e:
                        print(f"Row {i+1}: Error setting status '{status}': {type(e).__name__}: {str(e)}, skipping")
                if motortype:
                    try:
                        old_mt = product.motortype.name if product.motortype else None
                        product.motortype = MotorTypes.objects.get(name=motortype)
                        if old_mt != motortype:
                            updated_fields.append(f"motortype='{motortype}'")
                    except MotorTypes.DoesNotExist:
                        print(f"Row {i+1}: MotorType '{motortype}' not found, skipping")
                if releasedate:
                    old_rd = product.releasedate
                    product.releasedate = pd.to_datetime(releasedate).date() if isinstance(releasedate, str) else releasedate
                    if old_rd != product.releasedate:
                        updated_fields.append(f"releasedate={product.releasedate}")
                if discontinueddate:
                    old_dd = product.discontinueddate
                    product.discontinueddate = pd.to_datetime(discontinueddate).date() if isinstance(discontinueddate, str) else discontinueddate
                    if old_dd != product.discontinueddate:
                        updated_fields.append(f"discontinueddate={product.discontinueddate}")
                if isaccessory is not None:
                    old_ia = product.isaccessory
                    product.isaccessory = bool(isaccessory)
                    if old_ia != product.isaccessory:
                        updated_fields.append(f"isaccessory={product.isaccessory}")
                
                # ManyToMany fields - use .add() only
                if itemtype:
                    try:
                        it_obj = ItemTypes.objects.get(fullname=itemtype)
                        if not product.itemtypes.filter(pk=it_obj.pk).exists():
                            product.itemtypes.add(it_obj)
                            m2m_added.append(f"itemtype='{itemtype}'")
                    except ItemTypes.DoesNotExist:
                        print(f"Row {i+1}: ItemType '{itemtype}' not found, skipping")
                if subcategory:
                    try:
                        sc_obj = Subcategories.objects.get(fullname=subcategory)
                        if not product.subcategories.filter(pk=sc_obj.pk).exists():
                            product.subcategories.add(sc_obj)
                            m2m_added.append(f"subcategory='{subcategory}'")
                    except Subcategories.DoesNotExist:
                        print(f"Row {i+1}: Subcategory '{subcategory}' not found, skipping")
                if category:
                    try:
                        cat_obj = Categories.objects.get(fullname=category)
                        if not product.categories.filter(pk=cat_obj.pk).exists():
                            product.categories.add(cat_obj)
                            m2m_added.append(f"category='{category}'")
                    except Categories.DoesNotExist:
                        print(f"Row {i+1}: Category '{category}' not found, skipping")
                if batteryplatform:
                    try:
                        bp_obj = BatteryPlatforms.objects.get(name=batteryplatform)
                        if not product.batteryplatforms.filter(pk=bp_obj.pk).exists():
                            product.batteryplatforms.add(bp_obj)
                            m2m_added.append(f"batteryplatform='{batteryplatform}'")
                    except BatteryPlatforms.DoesNotExist:
                        print(f"Row {i+1}: BatteryPlatform '{batteryplatform}' not found, skipping")
                if batteryvoltage:
                    try:
                        bv_obj = BatteryVoltages.objects.get(value=int(batteryvoltage))
                        if not product.batteryvoltages.filter(pk=bv_obj.pk).exists():
                            product.batteryvoltages.add(bv_obj)
                            m2m_added.append(f"batteryvoltage={batteryvoltage}")
                    except BatteryVoltages.DoesNotExist:
                        print(f"Row {i+1}: BatteryVoltage '{batteryvoltage}' not found, skipping")
                if features:
                    feature_names = [f.strip() for f in str(features).split(',')]
                    for feat_name in feature_names:
                        try:
                            feat_obj = Features.objects.get(name=feat_name)
                            if not product.features.filter(pk=feat_obj.pk).exists():
                                product.features.add(feat_obj)
                                m2m_added.append(f"feature='{feat_name}'")
                        except Features.DoesNotExist:
                            print(f"Row {i+1}: Feature '{feat_name}' not found")
                
                product.save()
                if updated_fields or m2m_added:
                    all_changes = updated_fields + m2m_added
                    changes_str = ', '.join(all_changes)
                    print(f"Row {i+1}: Product {product.brand.name} {product.sku} ({product.name}) updated - Fields: {changes_str}")
                else:
                    print(f"Row {i+1}: Product {product.brand.name} {product.sku} ({product.name}) updated (no fields changed)")
            except Products.DoesNotExist:
                print(f"Row {i+1}: Product not found for update")
    elif action == 'purge':
        if product_sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                product = Products.objects.get(sku=product_sku, brand=brand_obj)
                
                columns_to_purge = [col for col in df.columns if col.lower() not in ['action', 'brand', 'product_sku', 'recordtype']]
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
        if product_sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                try:
                    product = Products.objects.get(sku=product_sku, brand=brand_obj)
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
                    if product_sku:
                        create_data['sku'] = product_sku
                    if image is not None:
                        create_data['image'] = image
                    if listingtype:
                        try:
                            create_data['listingtype'] = ListingTypes.objects.get(name=listingtype)
                        except ListingTypes.DoesNotExist:
                            print(f"Row {i+1}: ListingType '{listingtype}' not found, skipping")
                    if status:
                        try:
                            status_obj = Statuses.objects.get(name=str(status).strip())
                            create_data['status'] = status_obj
                        except Statuses.DoesNotExist:
                            print(f"Row {i+1}: Status '{status}' not found, skipping")
                        except Exception as e:
                            print(f"Row {i+1}: Error setting status '{status}': {type(e).__name__}: {str(e)}, skipping")
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
    component_sku = get_col(row, 'component_sku', df)
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
        if component_sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                component.delete()
                print(f"Row {i+1}: Component {component.name} deleted")
            except Brands.DoesNotExist:
                print(f"Row {i+1}: Brand '{brand}' not found")
            except Components.DoesNotExist:
                print(f"Row {i+1}: Component not found")
    elif action == 'update':
        if component_sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                
                updated_fields = []
                m2m_added = []
                
                if name is not None:
                    old_name = component.name
                    component.name = name
                    if old_name != name:
                        updated_fields.append(f"name='{name}'")
                if description is not None:
                    old_desc = component.description
                    component.description = description
                    if old_desc != description:
                        desc_str = f"{description[:50]}..." if description and len(str(description)) > 50 else str(description)
                        updated_fields.append(f"description='{desc_str}'")
                if image is not None:
                    old_img = component.image
                    component.image = image
                    if old_img != image:
                        updated_fields.append(f"image='{image}'")
                if listingtype:
                    try:
                        old_lt = component.listingtype.name if component.listingtype else None
                        component.listingtype = ListingTypes.objects.get(name=listingtype)
                        if old_lt != listingtype:
                            updated_fields.append(f"listingtype='{listingtype}'")
                    except ListingTypes.DoesNotExist:
                        print(f"Row {i+1}: ListingType '{listingtype}' not found, skipping")
                if motortype:
                    try:
                        old_mt = component.motortype.name if component.motortype else None
                        component.motortype = MotorTypes.objects.get(name=motortype)
                        if old_mt != motortype:
                            updated_fields.append(f"motortype='{motortype}'")
                    except MotorTypes.DoesNotExist:
                        print(f"Row {i+1}: MotorType '{motortype}' not found, skipping")
                if is_featured is not None:
                    old_if = component.is_featured
                    component.is_featured = bool(is_featured)
                    if old_if != component.is_featured:
                        updated_fields.append(f"is_featured={component.is_featured}")
                if standalone_price is not None:
                    old_sp = component.standalone_price
                    component.standalone_price = float(standalone_price)
                    if old_sp != component.standalone_price:
                        updated_fields.append(f"standalone_price={component.standalone_price}")
                if showcase_priority is not None:
                    old_sc = component.showcase_priority
                    component.showcase_priority = int(showcase_priority)
                    if old_sc != component.showcase_priority:
                        updated_fields.append(f"showcase_priority={component.showcase_priority}")
                if isaccessory is not None:
                    old_ia = component.isaccessory
                    component.isaccessory = bool(isaccessory)
                    if old_ia != component.isaccessory:
                        updated_fields.append(f"isaccessory={component.isaccessory}")
                
                # ManyToMany fields - use .add() only
                if itemtype:
                    try:
                        it_obj = ItemTypes.objects.get(fullname=itemtype)
                        if not component.itemtypes.filter(pk=it_obj.pk).exists():
                            component.itemtypes.add(it_obj)
                            m2m_added.append(f"itemtype='{itemtype}'")
                    except ItemTypes.DoesNotExist:
                        print(f"Row {i+1}: ItemType '{itemtype}' not found, skipping")
                if subcategory:
                    try:
                        sc_obj = Subcategories.objects.get(fullname=subcategory)
                        if not component.subcategories.filter(pk=sc_obj.pk).exists():
                            component.subcategories.add(sc_obj)
                            m2m_added.append(f"subcategory='{subcategory}'")
                    except Subcategories.DoesNotExist:
                        print(f"Row {i+1}: Subcategory '{subcategory}' not found, skipping")
                if category:
                    try:
                        cat_obj = Categories.objects.get(fullname=category)
                        if not component.categories.filter(pk=cat_obj.pk).exists():
                            component.categories.add(cat_obj)
                            m2m_added.append(f"category='{category}'")
                    except Categories.DoesNotExist:
                        print(f"Row {i+1}: Category '{category}' not found, skipping")
                if batteryplatform:
                    try:
                        bp_obj = BatteryPlatforms.objects.get(name=batteryplatform)
                        if not component.batteryplatforms.filter(pk=bp_obj.pk).exists():
                            component.batteryplatforms.add(bp_obj)
                            m2m_added.append(f"batteryplatform='{batteryplatform}'")
                    except BatteryPlatforms.DoesNotExist:
                        print(f"Row {i+1}: BatteryPlatform '{batteryplatform}' not found, skipping")
                if batteryvoltage:
                    try:
                        bv_obj = BatteryVoltages.objects.get(value=int(batteryvoltage))
                        if not component.batteryvoltages.filter(pk=bv_obj.pk).exists():
                            component.batteryvoltages.add(bv_obj)
                            m2m_added.append(f"batteryvoltage={batteryvoltage}")
                    except BatteryVoltages.DoesNotExist:
                        print(f"Row {i+1}: BatteryVoltage '{batteryvoltage}' not found, skipping")
                if productline:
                    try:
                        pl_obj = ProductLines.objects.get(name=productline)
                        if not component.productlines.filter(pk=pl_obj.pk).exists():
                            component.productlines.add(pl_obj)
                            m2m_added.append(f"productline='{productline}'")
                    except ProductLines.DoesNotExist:
                        print(f"Row {i+1}: ProductLine '{productline}' not found, skipping")
                if features:
                    feature_names = [f.strip() for f in str(features).split(',')]
                    for feat_name in feature_names:
                        try:
                            feat_obj = Features.objects.get(name=feat_name)
                            if not component.features.filter(pk=feat_obj.pk).exists():
                                component.features.add(feat_obj)
                                m2m_added.append(f"feature='{feat_name}'")
                        except Features.DoesNotExist:
                            print(f"Row {i+1}: Feature '{feat_name}' not found")
                
                component.save()
                if updated_fields or m2m_added:
                    all_changes = updated_fields + m2m_added
                    changes_str = ', '.join(all_changes)
                    print(f"Row {i+1}: Component {component.brand.name} {component.sku} ({component.name}) updated - Fields: {changes_str}")
                else:
                    print(f"Row {i+1}: Component {component.brand.name} {component.sku} ({component.name}) updated (no fields changed)")
            except Components.DoesNotExist:
                print(f"Row {i+1}: Component not found for update")
    elif action == 'purge':
        if component_sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                
                columns_to_purge = [col for col in df.columns if col.lower() not in ['action', 'brand', 'component_sku', 'recordtype']]
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
        if component_sku and brand:
            try:
                brand_obj = Brands.objects.get(name=brand)
                try:
                    component = Components.objects.get(sku=component_sku, brand=brand_obj)
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
                    if component_sku:
                        create_data['sku'] = component_sku
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
                    updated_fields = []
                    if value is not None:
                        old_value = comp_feature.value
                        comp_feature.value = value
                        if old_value != value:
                            updated_fields.append(f"value='{value}'")
                    
                    if updated_fields:
                        comp_feature.save()
                        fields_str = ', '.join(updated_fields)
                        print(f"Row {i+1}: ComponentFeature updated - Component: {component.brand.name} {component.sku}, Feature: {feature}, Fields: {fields_str}")
                    else:
                        if value is not None:
                            print(f"Row {i+1}: ComponentFeature updated - Component: {component.brand.name} {component.sku}, Feature: {feature}, Fields: value='{value}' (no change)")
                        else:
                            print(f"Row {i+1}: ComponentFeature updated - Component: {component.brand.name} {component.sku}, Feature: {feature} (no fields provided)")
                except ComponentFeatures.DoesNotExist:
                    comp_feature = ComponentFeatures.objects.create(component=component, feature=feature_obj, value=value)
                    component.features.add(feature_obj)
                    value_str = f"value='{value}'" if value else "value=None"
                    print(f"Row {i+1}: ComponentFeature created - Component: {component.brand.name} {component.sku}, Feature: {feature}, {value_str}")
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
                        deleted_value = comp_attr.value if comp_attr.value else None
                        comp_attr.delete()
                        value_info = f", Value: '{deleted_value}'" if deleted_value else ""
                        print(f"Row {i+1}: ComponentAttribute deleted - Component: {component.brand.name} {component.sku}, Attribute: {attribute}{value_info}")
                    else:
                        print(f"Row {i+1}: ComponentAttribute not found - Component: {component.brand.name} {component.sku}, Attribute: {attribute}")
                except ComponentAttributes.DoesNotExist:
                    print(f"Row {i+1}: ComponentAttribute not found - Component: {component.brand.name} {component.sku}, Attribute: {attribute}")
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
                        updated_fields = []
                        if value is not None:
                            old_value = comp_attr.value
                            comp_attr.value = value
                            if old_value != value:
                                updated_fields.append(f"value='{value}'")
                        
                        if updated_fields:
                            comp_attr.save()
                            fields_str = ', '.join(updated_fields)
                            print(f"Row {i+1}: ComponentAttribute updated - Component: {component.brand.name} {component.sku}, Attribute: {attribute}, Fields: {fields_str}")
                        else:
                            # Show what was attempted even if no change
                            if value is not None:
                                print(f"Row {i+1}: ComponentAttribute updated - Component: {component.brand.name} {component.sku}, Attribute: {attribute}, Fields: value='{value}' (no change from existing)")
                            else:
                                print(f"Row {i+1}: ComponentAttribute updated - Component: {component.brand.name} {component.sku}, Attribute: {attribute} (no fields provided)")
                except ComponentAttributes.DoesNotExist:
                    ComponentAttributes.objects.create(component=component, attribute=attr_obj, value=value)
                    value_str = f"value='{value}'" if value else "value=None"
                    print(f"Row {i+1}: ComponentAttribute created - Component: {component.brand.name} {component.sku}, Attribute: {attribute}, {value_str}")
            except (Brands.DoesNotExist, Components.DoesNotExist, Attributes.DoesNotExist) as e:
                print(f"Row {i+1}: {type(e).__name__}")
    elif action == 'purge':
        if brand and component_sku:
            try:
                brand_obj = Brands.objects.get(name=brand)
                component = Components.objects.get(sku=component_sku, brand=brand_obj)
                count = ComponentAttributes.objects.filter(component=component).count()
                ComponentAttributes.objects.filter(component=component).delete()
                print(f"Row {i+1}: ComponentAttribute purged - Component: {component.brand.name} {component.sku}, Purged {count} attribute(s)")
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
                    old_qty = prod_comp.quantity
                    prod_comp.quantity = int(quantity)
                    if old_qty != prod_comp.quantity:
                        prod_comp.save()
                        print(f"Row {i+1}: ProductComponent updated - Product: {product.brand.name} {product.sku}, Component: {component.brand.name} {component.sku}, Fields: quantity={prod_comp.quantity}")
                    else:
                        print(f"Row {i+1}: ProductComponent updated - Product: {product.brand.name} {product.sku}, Component: {component.brand.name} {component.sku}, Fields: quantity={quantity} (no change)")
                except ProductComponents.DoesNotExist:
                    ProductComponents.objects.create(product=product, component=component, quantity=int(quantity))
                    print(f"Row {i+1}: ProductComponent created - Product: {product.brand.name} {product.sku}, Component: {component.brand.name} {component.sku}, quantity={quantity}")
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
                    old_qty = prod_acc.quantity
                    prod_acc.quantity = int(quantity)
                    if old_qty != prod_acc.quantity:
                        prod_acc.save()
                        print(f"Row {i+1}: ProductAccessory updated - Product: {product.brand.name} {product.sku}, Name: {name}, Fields: quantity={prod_acc.quantity}")
                    else:
                        print(f"Row {i+1}: ProductAccessory updated - Product: {product.brand.name} {product.sku}, Name: {name}, Fields: quantity={quantity} (no change)")
                except ProductAccessories.DoesNotExist:
                    ProductAccessories.objects.create(product=product, name=name, quantity=int(quantity))
                    print(f"Row {i+1}: ProductAccessory created - Product: {product.brand.name} {product.sku}, Name: {name}, quantity={quantity}")
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
                    updated_fields = []
                    if value is not None:
                        old_value = prod_spec.value
                        prod_spec.value = value
                        if old_value != value:
                            updated_fields.append(f"value='{value}'")
                    
                    if updated_fields:
                        prod_spec.save()
                        fields_str = ', '.join(updated_fields)
                        print(f"Row {i+1}: ProductSpecification updated - Product: {product.brand.name} {product.sku}, Name: {name}, Fields: {fields_str}")
                    else:
                        if value is not None:
                            print(f"Row {i+1}: ProductSpecification updated - Product: {product.brand.name} {product.sku}, Name: {name}, Fields: value='{value}' (no change)")
                        else:
                            print(f"Row {i+1}: ProductSpecification updated - Product: {product.brand.name} {product.sku}, Name: {name} (no fields provided)")
                except ProductSpecifications.DoesNotExist:
                    ProductSpecifications.objects.create(product=product, name=name, value=value)
                    value_str = f"value='{value}'" if value else "value=None"
                    print(f"Row {i+1}: ProductSpecification created - Product: {product.brand.name} {product.sku}, Name: {name}, {value_str}")
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
    displayformat = get_col(row, 'displayformat', df)
    
    if action == 'delete':
        if name:
            try:
                attr = Attributes.objects.get(name=name)
                attr.delete()
                print(f"Row {i+1}: Attribute {name} deleted")
            except Attributes.DoesNotExist:
                print(f"Row {i+1}: Attribute not found")
    elif action == 'update':
        if name:
            try:
                attr = Attributes.objects.get(name=name)
                
                updated_fields = []
                # Track what fields are being updated
                if unit is not None:
                    old_unit = attr.unit
                    attr.unit = unit
                    if old_unit != unit:
                        updated_fields.append(f"unit='{unit}'")
                if description is not None:
                    old_desc = attr.description
                    attr.description = description
                    if old_desc != description:
                        updated_fields.append(f"description='{description}'")
                if sortorder is not None:
                    old_sort = attr.sortorder
                    attr.sortorder = int(sortorder)
                    if old_sort != attr.sortorder:
                        updated_fields.append(f"sortorder={sortorder}")
                if displayformat is not None:
                    old_df = attr.displayformat
                    attr.displayformat = displayformat
                    if old_df != displayformat:
                        updated_fields.append(f"displayformat='{displayformat}'")
                
                if updated_fields:
                    attr.save()
                    fields_str = ', '.join(updated_fields)
                    print(f"Row {i+1}: Attribute {name} updated - Fields: {fields_str}")
                else:
                    # Even if no actual changes, show what was in the update
                    attempted_fields = []
                    if unit is not None:
                        attempted_fields.append(f"unit='{unit}'")
                    if description is not None:
                        attempted_fields.append(f"description='{description}'")
                    if sortorder is not None:
                        attempted_fields.append(f"sortorder={sortorder}")
                    if displayformat is not None:
                        attempted_fields.append(f"displayformat='{displayformat}'")
                    if attempted_fields:
                        fields_str = ', '.join(attempted_fields)
                        print(f"Row {i+1}: Attribute {name} updated - Fields: {fields_str} (no change from existing values)")
                    else:
                        print(f"Row {i+1}: Attribute {name} updated (no fields provided)")
            except Attributes.DoesNotExist:
                print(f"Row {i+1}: Attribute not found")
    elif action == 'create':
        if name:
            try:
                # Check if attribute already exists (by name only, since name is unique)
                Attributes.objects.get(name=name)
                print(f"Row {i+1}: Attribute {name} already exists, updating instead")
                handle_attribute(row, i, 'update', df, sheet_name)
            except Attributes.DoesNotExist:
                create_data = {'name': name}
                if unit is not None:
                    create_data['unit'] = unit
                if description is not None:
                    create_data['description'] = description
                if sortorder is not None:
                    create_data['sortorder'] = int(sortorder)
                if displayformat is not None:
                    create_data['displayformat'] = displayformat
                
                Attributes.objects.create(**create_data)
                
                # Show what was created
                created_fields = []
                if unit is not None:
                    created_fields.append(f"unit='{unit}'")
                if description is not None:
                    created_fields.append(f"description='{description}'")
                if sortorder is not None:
                    created_fields.append(f"sortorder={sortorder}")
                if displayformat is not None:
                    created_fields.append(f"displayformat='{displayformat}'")
                
                if created_fields:
                    fields_str = ', '.join(created_fields)
                    print(f"Row {i+1}: Attribute {name} created - Fields: {fields_str}")
                else:
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
                updated_fields = []
                if description is not None:
                    old_desc = feat.description
                    feat.description = description
                    if old_desc != description:
                        updated_fields.append(f"description='{description}'")
                if sortorder is not None:
                    old_sort = feat.sortorder
                    feat.sortorder = int(sortorder)
                    if old_sort != feat.sortorder:
                        updated_fields.append(f"sortorder={feat.sortorder}")
                
                if updated_fields:
                    feat.save()
                    fields_str = ', '.join(updated_fields)
                    print(f"Row {i+1}: Feature {name} updated - Fields: {fields_str}")
                else:
                    attempted_fields = []
                    if description is not None:
                        attempted_fields.append(f"description='{description}'")
                    if sortorder is not None:
                        attempted_fields.append(f"sortorder={sortorder}")
                    if attempted_fields:
                        fields_str = ', '.join(attempted_fields)
                        print(f"Row {i+1}: Feature {name} updated - Fields: {fields_str} (no change)")
                    else:
                        print(f"Row {i+1}: Feature {name} updated (no fields provided)")
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
                updated_fields = []
                if name is not None:
                    old_name = cat.name
                    cat.name = name
                    if old_name != name:
                        updated_fields.append(f"name='{name}'")
                if sortorder is not None:
                    old_sort = cat.sortorder
                    cat.sortorder = int(sortorder)
                    if old_sort != cat.sortorder:
                        updated_fields.append(f"sortorder={cat.sortorder}")
                
                if updated_fields:
                    cat.save()
                    fields_str = ', '.join(updated_fields)
                    print(f"Row {i+1}: Category {fullname} updated - Fields: {fields_str}")
                else:
                    attempted_fields = []
                    if name is not None:
                        attempted_fields.append(f"name='{name}'")
                    if sortorder is not None:
                        attempted_fields.append(f"sortorder={sortorder}")
                    if attempted_fields:
                        fields_str = ', '.join(attempted_fields)
                        print(f"Row {i+1}: Category {fullname} updated - Fields: {fields_str} (no change)")
                    else:
                        print(f"Row {i+1}: Category {fullname} updated (no fields provided)")
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
                updated_fields = []
                m2m_added = []
                if name is not None:
                    old_name = subcat.name
                    subcat.name = name
                    if old_name != name:
                        updated_fields.append(f"name='{name}'")
                if sortorder is not None:
                    old_sort = subcat.sortorder
                    subcat.sortorder = int(sortorder)
                    if old_sort != subcat.sortorder:
                        updated_fields.append(f"sortorder={subcat.sortorder}")
                if category_fullname:
                    try:
                        cat = Categories.objects.get(fullname=category_fullname)
                        if not subcat.categories.filter(pk=cat.pk).exists():
                            subcat.categories.add(cat)
                            m2m_added.append(f"category='{category_fullname}'")
                    except Categories.DoesNotExist:
                        print(f"Row {i+1}: Category '{category_fullname}' not found")
                
                if updated_fields or m2m_added:
                    subcat.save()
                    all_changes = updated_fields + m2m_added
                    fields_str = ', '.join(all_changes)
                    print(f"Row {i+1}: Subcategory {fullname} updated - Fields: {fields_str}")
                else:
                    attempted_fields = []
                    if name is not None:
                        attempted_fields.append(f"name='{name}'")
                    if sortorder is not None:
                        attempted_fields.append(f"sortorder={sortorder}")
                    if attempted_fields:
                        fields_str = ', '.join(attempted_fields)
                        print(f"Row {i+1}: Subcategory {fullname} updated - Fields: {fields_str} (no change)")
                    else:
                        print(f"Row {i+1}: Subcategory {fullname} updated (no fields provided)")
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
                updated_fields = []
                m2m_added = []
                if name is not None:
                    old_name = itemtype.name
                    itemtype.name = name
                    if old_name != name:
                        updated_fields.append(f"name='{name}'")
                if sortorder is not None:
                    old_sort = itemtype.sortorder
                    itemtype.sortorder = int(sortorder)
                    if old_sort != itemtype.sortorder:
                        updated_fields.append(f"sortorder={itemtype.sortorder}")
                if category_fullname:
                    try:
                        cat_obj = Categories.objects.get(fullname=category_fullname)
                        if not itemtype.categories.filter(pk=cat_obj.pk).exists():
                            itemtype.categories.add(cat_obj)
                            m2m_added.append(f"category='{category_fullname}'")
                    except Categories.DoesNotExist:
                        print(f"Row {i+1}: Category '{category_fullname}' not found")
                if subcategory_fullname:
                    try:
                        sc_obj = Subcategories.objects.get(fullname=subcategory_fullname)
                        if not itemtype.subcategories.filter(pk=sc_obj.pk).exists():
                            itemtype.subcategories.add(sc_obj)
                            m2m_added.append(f"subcategory='{subcategory_fullname}'")
                    except Subcategories.DoesNotExist:
                        print(f"Row {i+1}: Subcategory '{subcategory_fullname}' not found")
                if attribute_name:
                    try:
                        attr_obj = Attributes.objects.get(name=attribute_name)
                        if not itemtype.attributes.filter(pk=attr_obj.pk).exists():
                            itemtype.attributes.add(attr_obj)
                            m2m_added.append(f"attribute='{attribute_name}'")
                    except Attributes.DoesNotExist:
                        print(f"Row {i+1}: Attribute '{attribute_name}' not found")
                
                if updated_fields or m2m_added:
                    itemtype.save()
                    all_changes = updated_fields + m2m_added
                    fields_str = ', '.join(all_changes)
                    print(f"Row {i+1}: ItemType {fullname} updated - Fields: {fields_str}")
                else:
                    attempted_fields = []
                    if name is not None:
                        attempted_fields.append(f"name='{name}'")
                    if sortorder is not None:
                        attempted_fields.append(f"sortorder={sortorder}")
                    if attempted_fields:
                        fields_str = ', '.join(attempted_fields)
                        print(f"Row {i+1}: ItemType {fullname} updated - Fields: {fields_str} (no change)")
                    else:
                        print(f"Row {i+1}: ItemType {fullname} updated (no fields provided)")
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
                updated_fields = []
                if sortorder is not None:
                    old_sort = mt.sortorder
                    mt.sortorder = int(sortorder)
                    if old_sort != mt.sortorder:
                        updated_fields.append(f"sortorder={mt.sortorder}")
                
                if updated_fields:
                    mt.save()
                    fields_str = ', '.join(updated_fields)
                    print(f"Row {i+1}: MotorType {name} updated - Fields: {fields_str}")
                else:
                    if sortorder is not None:
                        print(f"Row {i+1}: MotorType {name} updated - Fields: sortorder={sortorder} (no change)")
                    else:
                        print(f"Row {i+1}: MotorType {name} updated (no fields provided)")
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
                updated_fields = []
                if retailer:
                    try:
                        old_ret = lt.retailer.name if lt.retailer else None
                        lt.retailer = Retailers.objects.get(name=retailer)
                        if old_ret != retailer:
                            updated_fields.append(f"retailer='{retailer}'")
                    except Retailers.DoesNotExist:
                        print(f"Row {i+1}: Retailer '{retailer}' not found")
                elif retailer is None:
                    old_ret = lt.retailer.name if lt.retailer else None
                    lt.retailer = None
                    if old_ret is not None:
                        updated_fields.append("retailer=None")
                
                if updated_fields:
                    lt.save()
                    fields_str = ', '.join(updated_fields)
                    print(f"Row {i+1}: ListingType {name} updated - Fields: {fields_str}")
                else:
                    if retailer is not None:
                        print(f"Row {i+1}: ListingType {name} updated - Fields: retailer='{retailer}' (no change)")
                    else:
                        print(f"Row {i+1}: ListingType {name} updated (no fields provided)")
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
                updated_fields = []
                if color is not None:
                    old_color = brand.color
                    brand.color = color
                    if old_color != color:
                        updated_fields.append(f"color='{color}'")
                if logo is not None:
                    old_logo = brand.logo
                    brand.logo = logo
                    if old_logo != logo:
                        updated_fields.append(f"logo='{logo}'")
                if sortorder is not None:
                    old_sort = brand.sortorder
                    brand.sortorder = int(sortorder)
                    if old_sort != brand.sortorder:
                        updated_fields.append(f"sortorder={brand.sortorder}")
                
                if updated_fields:
                    brand.save()
                    fields_str = ', '.join(updated_fields)
                    print(f"Row {i+1}: Brand {name} updated - Fields: {fields_str}")
                else:
                    attempted_fields = []
                    if color is not None:
                        attempted_fields.append(f"color='{color}'")
                    if logo is not None:
                        attempted_fields.append(f"logo='{logo}'")
                    if sortorder is not None:
                        attempted_fields.append(f"sortorder={sortorder}")
                    if attempted_fields:
                        fields_str = ', '.join(attempted_fields)
                        print(f"Row {i+1}: Brand {name} updated - Fields: {fields_str} (no change)")
                    else:
                        print(f"Row {i+1}: Brand {name} updated (no fields provided)")
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
                updated_fields = []
                if url is not None:
                    old_url = retailer.url
                    retailer.url = url
                    if old_url != url:
                        updated_fields.append(f"url='{url}'")
                if logo is not None:
                    old_logo = retailer.logo
                    retailer.logo = logo
                    if old_logo != logo:
                        updated_fields.append(f"logo='{logo}'")
                if sortorder is not None:
                    old_sort = retailer.sortorder
                    retailer.sortorder = int(sortorder)
                    if old_sort != retailer.sortorder:
                        updated_fields.append(f"sortorder={retailer.sortorder}")
                
                if updated_fields:
                    retailer.save()
                    fields_str = ', '.join(updated_fields)
                    print(f"Row {i+1}: Retailer {name} updated - Fields: {fields_str}")
                else:
                    attempted_fields = []
                    if url is not None:
                        attempted_fields.append(f"url='{url}'")
                    if logo is not None:
                        attempted_fields.append(f"logo='{logo}'")
                    if sortorder is not None:
                        attempted_fields.append(f"sortorder={sortorder}")
                    if attempted_fields:
                        fields_str = ', '.join(attempted_fields)
                        print(f"Row {i+1}: Retailer {name} updated - Fields: {fields_str} (no change)")
                    else:
                        print(f"Row {i+1}: Retailer {name} updated (no fields provided)")
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
                updated_fields = []
                if color is not None:
                    old_color = status.color
                    status.color = color
                    if old_color != color:
                        updated_fields.append(f"color='{color}'")
                if icon is not None:
                    old_icon = status.icon
                    status.icon = icon
                    if old_icon != icon:
                        updated_fields.append(f"icon='{icon}'")
                if sortorder is not None:
                    old_sort = status.sortorder
                    status.sortorder = int(sortorder)
                    if old_sort != status.sortorder:
                        updated_fields.append(f"sortorder={status.sortorder}")
                
                if updated_fields:
                    status.save()
                    fields_str = ', '.join(updated_fields)
                    print(f"Row {i+1}: Status {name} updated - Fields: {fields_str}")
                else:
                    attempted_fields = []
                    if color is not None:
                        attempted_fields.append(f"color='{color}'")
                    if icon is not None:
                        attempted_fields.append(f"icon='{icon}'")
                    if sortorder is not None:
                        attempted_fields.append(f"sortorder={sortorder}")
                    if attempted_fields:
                        fields_str = ', '.join(attempted_fields)
                        print(f"Row {i+1}: Status {name} updated - Fields: {fields_str} (no change)")
                    else:
                        print(f"Row {i+1}: Status {name} updated (no fields provided)")
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
                updated_fields = []
                m2m_added = []
                if brand:
                    try:
                        old_brand = bp.brand.name if bp.brand else None
                        bp.brand = Brands.objects.get(name=brand)
                        if old_brand != brand:
                            updated_fields.append(f"brand='{brand}'")
                    except Brands.DoesNotExist:
                        print(f"Row {i+1}: Brand '{brand}' not found")
                elif brand is None:
                    old_brand = bp.brand.name if bp.brand else None
                    bp.brand = None
                    if old_brand is not None:
                        updated_fields.append("brand=None")
                if voltage_value is not None:
                    try:
                        voltage = BatteryVoltages.objects.get(value=int(voltage_value))
                        if not bp.voltage.filter(pk=voltage.pk).exists():
                            bp.voltage.add(voltage)
                            m2m_added.append(f"voltage={voltage_value}")
                    except BatteryVoltages.DoesNotExist:
                        print(f"Row {i+1}: BatteryVoltage '{voltage_value}' not found")
                
                if updated_fields or m2m_added:
                    bp.save()
                    all_changes = updated_fields + m2m_added
                    fields_str = ', '.join(all_changes)
                    print(f"Row {i+1}: BatteryPlatform {name} updated - Fields: {fields_str}")
                else:
                    attempted_fields = []
                    if brand is not None:
                        attempted_fields.append(f"brand='{brand}'")
                    if voltage_value is not None:
                        attempted_fields.append(f"voltage={voltage_value}")
                    if attempted_fields:
                        fields_str = ', '.join(attempted_fields)
                        print(f"Row {i+1}: BatteryPlatform {name} updated - Fields: {fields_str} (no change)")
                    else:
                        print(f"Row {i+1}: BatteryPlatform {name} updated (no fields provided)")
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
                updated_fields = []
                m2m_added = []
                if description is not None:
                    old_desc = pl.description
                    pl.description = description
                    if old_desc != description:
                        desc_str = f"{description[:50]}..." if description and len(str(description)) > 50 else str(description)
                        updated_fields.append(f"description='{desc_str}'")
                if image is not None:
                    old_img = pl.image
                    pl.image = image
                    if old_img != image:
                        updated_fields.append(f"image='{image}'")
                if batteryplatform_name:
                    try:
                        bp = BatteryPlatforms.objects.get(name=batteryplatform_name)
                        if not pl.batteryplatform.filter(pk=bp.pk).exists():
                            pl.batteryplatform.add(bp)
                            m2m_added.append(f"batteryplatform='{batteryplatform_name}'")
                    except BatteryPlatforms.DoesNotExist:
                        print(f"Row {i+1}: BatteryPlatform '{batteryplatform_name}' not found")
                if batteryvoltage_value is not None:
                    try:
                        bv = BatteryVoltages.objects.get(value=int(batteryvoltage_value))
                        if not pl.batteryvoltage.filter(pk=bv.pk).exists():
                            pl.batteryvoltage.add(bv)
                            m2m_added.append(f"batteryvoltage={batteryvoltage_value}")
                    except BatteryVoltages.DoesNotExist:
                        print(f"Row {i+1}: BatteryVoltage '{batteryvoltage_value}' not found")
                
                if updated_fields or m2m_added:
                    pl.save()
                    all_changes = updated_fields + m2m_added
                    fields_str = ', '.join(all_changes)
                    print(f"Row {i+1}: ProductLine {brand} {name} updated - Fields: {fields_str}")
                else:
                    attempted_fields = []
                    if description is not None:
                        attempted_fields.append(f"description='{description}'")
                    if image is not None:
                        attempted_fields.append(f"image='{image}'")
                    if attempted_fields:
                        fields_str = ', '.join(attempted_fields)
                        print(f"Row {i+1}: ProductLine {brand} {name} updated - Fields: {fields_str} (no change)")
                    else:
                        print(f"Row {i+1}: ProductLine {brand} {name} updated (no fields provided)")
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
                    updated_fields = []
                    if currency is not None:
                        old_curr = pl.currency
                        pl.currency = currency
                        if old_curr != currency:
                            updated_fields.append(f"currency='{currency}'")
                    if url is not None:
                        old_url = pl.url
                        pl.url = url
                        if old_url != url:
                            updated_fields.append(f"url='{url}'")
                    
                    if updated_fields:
                        pl.save()
                        fields_str = ', '.join(updated_fields)
                        print(f"Row {i+1}: PriceListing updated - Product: {product.brand.name} {product.sku}, Retailer: {retailer_name}, Price: {create_data['price']} {create_data['currency']}, Fields: {fields_str}")
                    else:
                        print(f"Row {i+1}: PriceListing updated - Product: {product.brand.name} {product.sku}, Retailer: {retailer_name}, Price: {create_data['price']} {create_data['currency']} (no fields changed)")
                except PriceListings.DoesNotExist:
                    PriceListings.objects.create(**create_data)
                    retailer_sku_str = f", RetailerSKU: {retailer_sku}" if retailer_sku else ""
                    url_str = f", URL: {url}" if url else ""
                    print(f"Row {i+1}: PriceListing created - Product: {product.brand.name} {product.sku}, Retailer: {retailer_name}, Price: {create_data['price']} {create_data['currency']}{retailer_sku_str}{url_str}")
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

def process_sheet(file_path, sheet_name, excel_file, results_collector=None):
    """Process a single sheet from the Excel file and collect results"""
    print(f"\n{'='*60}")
    print(f"Processing sheet: {sheet_name}")
    print(f"{'='*60}")
    
    try:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        print(f"Loaded {len(df)} rows and {len(df.columns)} columns")
        
        if len(df) == 0:
            msg = f"Sheet '{sheet_name}' is empty, skipping"
            print(msg)
            if results_collector:
                results_collector['warnings'].append(msg)
            return
        
        for i in range(len(df)):
            row = df.iloc[i]
            
            if 'action' not in df.columns:
                msg = f"Sheet '{sheet_name}', Row {i+1}: Skipping - 'action' column not found"
                print(msg)
                if results_collector:
                    results_collector['warnings'].append(msg)
                    results_collector['warning_count'] += 1
                continue
            
            if 'recordtype' not in df.columns:
                msg = f"Sheet '{sheet_name}', Row {i+1}: Skipping - 'recordtype' column not found"
                print(msg)
                if results_collector:
                    results_collector['warnings'].append(msg)
                    results_collector['warning_count'] += 1
                continue
            
            action = get_col(row, 'action', df)
            recordtype = get_col(row, 'recordtype', df)
            
            if not action:
                continue
            
            if not recordtype:
                msg = f"Sheet '{sheet_name}', Row {i+1}: Skipping - recordtype is empty"
                print(msg)
                if results_collector:
                    results_collector['warnings'].append(msg)
                    results_collector['warning_count'] += 1
                continue
            
            recordtype_lower = str(recordtype).lower().strip()
            action_lower = str(action).lower().strip()
            
            if recordtype_lower in ROUTERS:
                original_stdout = sys.stdout
                output_capture = None
                try:
                    # Capture output to get detailed operation messages
                    if results_collector:
                        # Create output capture to get detailed messages
                        output_capture = OutputCapture(original_stdout, results_collector)
                        sys.stdout = output_capture
                    
                    # Call the handler - it will print detailed messages
                    ROUTERS[recordtype_lower](row, i, action, df, sheet_name)
                    
                    # Flush stdout to ensure all print statements are captured
                    sys.stdout.flush()
                    
                    # Flush output capture to ensure all messages are processed
                    details_before = len(results_collector['details']) if results_collector else 0
                    if output_capture:
                        output_capture.flush()
                    
                    # Track success
                    if results_collector:
                        results_collector['success_count'] += 1
                        results_collector['by_action'][action_lower] += 1
                        results_collector['by_recordtype'][recordtype_lower] += 1
                        results_collector['total_rows'] += 1
                        
                        # Fallback: If no detail was captured but operation succeeded, create one with field details
                        details_after = len(results_collector['details'])
                        if details_before == details_after:
                            # Try to get record identifier for better detail message
                            record_id = ""
                            if recordtype_lower == 'product':
                                product_sku = get_col(row, 'product_sku', df)
                                brand = get_col(row, 'brand', df)
                                if product_sku and brand:
                                    record_id = f"{brand} {product_sku}"
                            elif recordtype_lower == 'component':
                                component_sku = get_col(row, 'component_sku', df)
                                brand = get_col(row, 'brand', df)
                                if component_sku and brand:
                                    record_id = f"{brand} {component_sku}"
                            elif recordtype_lower == 'attribute':
                                name = get_col(row, 'name', df)
                                if name:
                                    record_id = name
                            elif recordtype_lower in ['feature', 'category', 'subcategory', 'itemtype', 'motortype', 
                                                       'listingtype', 'brand', 'retailer', 'status', 'batteryplatform', 
                                                       'productline']:
                                name = get_col(row, 'name', df) or get_col(row, 'fullname', df)
                                if name:
                                    record_id = name
                            
                            # Collect updated fields (for UPDATE and PURGE actions)
                            updated_fields = []
                            if action_lower in ['update', 'purge']:
                                # Exclude key/identifier columns and action/recordtype columns
                                exclude_cols = {'action', 'recordtype', 'brand', 'component_sku', 
                                               'product_sku', 'component_brand', 'name', 'fullname'}
                                for col in df.columns:
                                    if col.lower() not in exclude_cols:
                                        value = get_col(row, col, df)
                                        if value is not None and value != '':
                                            if action_lower == 'update':
                                                # For update, show field and value
                                                if pd.notna(value):
                                                    updated_fields.append(f"{col}={value}")
                                            elif action_lower == 'purge':
                                                # For purge, just show field name
                                                updated_fields.append(col)
                            
                            # Create a detail entry matching handler format
                            # Format: "Row {i+1}: {RecordType} {identifier} {action_past_tense} [field details]"
                            record_type_display = recordtype_lower.replace('_', ' ').title().replace(' ', '')
                            if record_type_display == 'Componentfeature':
                                record_type_display = 'ComponentFeature'
                            elif record_type_display == 'Componentattribute':
                                record_type_display = 'ComponentAttribute'
                            elif record_type_display == 'Productcomponent':
                                record_type_display = 'ProductComponent'
                            elif record_type_display == 'Productaccessory':
                                record_type_display = 'ProductAccessory'
                            elif record_type_display == 'Productspecification':
                                record_type_display = 'ProductSpecification'
                            elif record_type_display == 'Productimage':
                                record_type_display = 'ProductImage'
                            elif record_type_display == 'Batteryvoltage':
                                record_type_display = 'BatteryVoltage'
                            elif record_type_display == 'Batteryplatform':
                                record_type_display = 'BatteryPlatform'
                            elif record_type_display == 'Productline':
                                record_type_display = 'ProductLine'
                            elif record_type_display == 'Pricelisting':
                                record_type_display = 'PriceListing'
                            
                            # Convert action to past tense to match handler format and grouping logic
                            action_past = {
                                'create': 'created',
                                'update': 'updated',
                                'delete': 'deleted',
                                'purge': 'purged'
                            }.get(action_lower, action_lower)
                            
                            # Build detail message with field information
                            if record_id:
                                detail_msg = f"Row {i+1}: {record_type_display} {record_id} {action_past}"
                            else:
                                detail_msg = f"Row {i+1}: {record_type_display} {action_past}"
                            
                            # Add field details for UPDATE and PURGE
                            if updated_fields:
                                if action_lower == 'update':
                                    detail_msg += f" - Fields: {', '.join(updated_fields)}"
                                elif action_lower == 'purge':
                                    detail_msg += f" - Purged fields: {', '.join(updated_fields)}"
                            
                            if len(results_collector['details']) < 1000:
                                results_collector['details'].append(detail_msg)
                except Exception as e:
                    # Flush before restoring in case of error
                    if output_capture:
                        sys.stdout.flush()
                        output_capture.flush()
                    error_msg = f"Sheet '{sheet_name}', Row {i+1}: Error processing {recordtype_lower}: {type(e).__name__}: {str(e)}"
                    print(error_msg)
                    if results_collector:
                        results_collector['errors'].append(error_msg)
                        results_collector['error_count'] += 1
                finally:
                    # Always restore stdout
                    if results_collector and output_capture:
                        sys.stdout = original_stdout
            else:
                msg = f"Sheet '{sheet_name}', Row {i+1}: Unknown recordtype '{recordtype}', skipping"
                print(msg)
                if results_collector:
                    results_collector['warnings'].append(msg)
                    results_collector['warning_count'] += 1
        
        print(f"\nCompleted processing sheet: {sheet_name}")
        
    except Exception as e:
        error_msg = f"Error processing sheet '{sheet_name}': {type(e).__name__}: {str(e)}"
        print(error_msg)
        if results_collector:
            results_collector['errors'].append(error_msg)
            results_collector['error_count'] += 1

# ============================================================================
# Main processing loop - process all selected sheets
# ============================================================================

# Analyze sheets and show preview dialog
print(f"\nAnalyzing {len(selected_sheets)} selected sheet(s)...")
summary = analyze_sheets(file_path, selected_sheets)

# Show preview dialog and get confirmation
root.deiconify()
root.update_idletasks()
confirmed = show_preview_dialog(root, summary)

if not confirmed:
    print("\nImport cancelled by user.")
    sys.exit(0)

# Initialize results collector
results = {
    'total_sheets': len(selected_sheets),
    'total_rows': 0,
    'success_count': 0,
    'error_count': 0,
    'warning_count': 0,
    'by_action': defaultdict(int),
    'by_recordtype': defaultdict(int),
    'errors': [],
    'warnings': [],
    'details': []
}

print(f"\nStarting import of {len(selected_sheets)} sheet(s)...")

total_sheets = len(selected_sheets)
for sheet_idx, sheet_name in enumerate(selected_sheets, 1):
    print(f"\n[{sheet_idx}/{total_sheets}] Processing sheet: {sheet_name}")
    process_sheet(file_path, sheet_name, excel_file, results)

print(f"\n{'='*60}")
print(f"Import complete! Processed {len(selected_sheets)} sheet(s)")
print(f"{'='*60}")
print(f"Successfully processed: {results['success_count']} rows")
print(f"Errors: {results['error_count']}")
print(f"Warnings: {results['warning_count']}")

# Show results dialog
root.deiconify()
root.update_idletasks()
show_results_dialog(root, results)

# Clean up
root.destroy()

