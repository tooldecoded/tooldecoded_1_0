import os
import django
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tooldecoded.settings')
django.setup()

from django.db import connection
import pandas as pd
from pathlib import Path

# Get the base directory (project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_FILE = BASE_DIR / 'dataimport' / 'all_tables_export.xlsx'

def get_all_table_names():
    """Get all table names from the database."""
    with connection.cursor() as cursor:
        # PostgreSQL query to get all table names from public schema
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        return [row[0] for row in cursor.fetchall()]

def export_table_to_dataframe(table_name):
    """Export a table to a pandas DataFrame."""
    try:
        # Use read_sql with Django connection - pandas supports Django DB connections
        query = f'SELECT * FROM "{table_name}"'
        # Get the underlying connection object
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            data = cursor.fetchall()
            df = pd.DataFrame(data, columns=columns)
        
        # Convert timezone-aware datetime columns to timezone-naive for Excel compatibility
        # Excel doesn't support timezone-aware datetimes
        for col in df.columns:
            try:
                # Check if column is datetime type (any variant)
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    # Remove timezone if present
                    if hasattr(df[col].dtype, 'tz') and df[col].dtype.tz is not None:
                        df[col] = df[col].dt.tz_localize(None)
                    elif df[col].dtype.name.startswith('datetime64'):
                        # Check individual values for timezone
                        try:
                            if df[col].notna().any() and df[col].dropna().iloc[0].tz is not None:
                                df[col] = df[col].dt.tz_localize(None)
                        except (AttributeError, IndexError):
                            pass
            except Exception:
                pass
            
            # Also check object columns for datetime-like values
            try:
                if df[col].dtype == 'object' and df[col].notna().any():
                    sample = df[col].dropna().iloc[0]
                    if isinstance(sample, pd.Timestamp):
                        # It's already a Timestamp, check for timezone
                        if sample.tz is not None:
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                            if df[col].notna().any():
                                df[col] = df[col].dt.tz_localize(None)
            except Exception:
                pass
        
        print(f"Exported {table_name}: {len(df)} rows, {len(df.columns)} columns")
        return df
    except Exception as e:
        print(f"Error exporting {table_name}: {str(e)}")
        return None

def export_all_tables():
    """Export all tables to an Excel file with multiple sheets."""
    print("Getting all table names...")
    table_names = get_all_table_names()
    print(f"Found {len(table_names)} tables")
    
    if not table_names:
        print("No tables found in database.")
        return
    
    print(f"\nExporting tables to {OUTPUT_FILE}...")
    
    # Create Excel writer object
    with pd.ExcelWriter(OUTPUT_FILE, engine='openpyxl') as writer:
        exported_count = 0
        for table_name in table_names:
            df = export_table_to_dataframe(table_name)
            if df is not None:
                # Excel sheet names can't be longer than 31 characters
                sheet_name = table_name[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                exported_count += 1
    
    print(f"\nExport complete!")
    print(f"Successfully exported {exported_count} out of {len(table_names)} tables")
    print(f"Output file: {OUTPUT_FILE}")

if __name__ == "__main__":
    export_all_tables()

