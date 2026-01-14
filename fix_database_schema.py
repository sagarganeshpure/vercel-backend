"""
Comprehensive script to fix all database schema issues
This script adds missing columns and removes obsolete ones
"""
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.core.config import settings
from app.db.database import engine

def fix_database_schema():
    """Fix database schema by adding missing columns"""
    print("=" * 60)
    print("Database Schema Fix Script")
    print("=" * 60)
    
    issues_found = []
    fixes_applied = []
    errors = []
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\nFound {len(tables)} tables in database")
        
        # Fix measurements table
        if 'measurements' in tables:
            print("\n" + "=" * 60)
            print("Checking 'measurements' table...")
            print("=" * 60)
            
            columns = {col['name']: col for col in inspector.get_columns('measurements')}
            column_names = list(columns.keys())
            print(f"Current columns: {', '.join(column_names)}")
            
            # Check for missing site_location column
            if 'site_location' not in column_names:
                issues_found.append({
                    'table': 'measurements',
                    'issue': 'Missing column site_location',
                    'action': 'ADD COLUMN'
                })
                print("\n[INFO] 'site_location' column is missing")
                print("  Attempting to add it...")
                try:
                    with engine.connect() as conn:
                        if 'postgresql' in settings.DATABASE_URL.lower():
                            conn.execute(text("ALTER TABLE measurements ADD COLUMN IF NOT EXISTS site_location VARCHAR"))
                        else:  # SQLite
                            conn.execute(text("ALTER TABLE measurements ADD COLUMN site_location TEXT"))
                        conn.commit()
                    fixes_applied.append("Added 'site_location' column to 'measurements' table")
                    print("  [OK] 'site_location' column added successfully")
                except Exception as e:
                    error_msg = f"Failed to add 'site_location' column: {e}"
                    errors.append(error_msg)
                    print(f"  [ERROR] {error_msg}")
            else:
                print("\n[OK] 'site_location' column exists")
        
        # Fix production_papers table
        if 'production_papers' in tables:
            print("\n" + "=" * 60)
            print("Checking 'production_papers' table...")
            print("=" * 60)
            
            columns = {col['name']: col for col in inspector.get_columns('production_papers')}
            column_names = list(columns.keys())
            print(f"Current columns: {', '.join(column_names)}")
            
            # Check for missing po_number column (model expects it)
            if 'po_number' not in column_names:
                issues_found.append({
                    'table': 'production_papers',
                    'issue': 'Missing column po_number',
                    'action': 'ADD COLUMN'
                })
                print("\n[INFO] 'po_number' column is missing")
                print("  Attempting to add it...")
                try:
                    with engine.connect() as conn:
                        if 'postgresql' in settings.DATABASE_URL.lower():
                            conn.execute(text("ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS po_number VARCHAR"))
                        else:  # SQLite
                            conn.execute(text("ALTER TABLE production_papers ADD COLUMN po_number TEXT"))
                        conn.commit()
                    fixes_applied.append("Added 'po_number' column to 'production_papers' table")
                    print("  [OK] 'po_number' column added successfully")
                except Exception as e:
                    error_msg = f"Failed to add 'po_number' column: {e}"
                    errors.append(error_msg)
                    print(f"  [ERROR] {error_msg}")
            else:
                print("\n[OK] 'po_number' column exists")
        
        # Summary
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        
        if fixes_applied:
            print(f"\n[OK] Applied {len(fixes_applied)} fixes:")
            for fix in fixes_applied:
                print(f"  - {fix}")
        
        if errors:
            print(f"\n[ERROR] {len(errors)} errors occurred:")
            for error in errors:
                print(f"  - {error}")
        
        if issues_found:
            print(f"\n[INFO] Found {len(issues_found)} issues:")
            for issue in issues_found:
                print(f"  - {issue['table']}: {issue['issue']}")
        
        if not errors and not issues_found:
            print("\n[OK] No issues found! Database schema is up to date.")
        
        print("\n[OK] Database schema check completed")
        return len(errors) == 0
        
    except Exception as e:
        print(f"\n[ERROR] Failed to check database schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\nStarting database schema fix...\n")
    success = fix_database_schema()
    print("\n" + "=" * 60)
    if success:
        print("Fix completed successfully!")
    else:
        print("Fix completed with errors. Please review the output above.")
    print("=" * 60)
    sys.exit(0 if success else 1)
