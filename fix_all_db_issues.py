"""
Comprehensive script to check and fix all database schema issues
This script:
1. Checks for missing columns (site_location)
2. Identifies obsolete columns (pd_number) 
3. Provides migration SQL
"""
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.core.config import settings
from app.db.database import engine

def check_and_fix_schema():
    """Check database schema and provide fixes"""
    print("=" * 60)
    print("Database Schema Check and Fix Script")
    print("=" * 60)
    
    issues_found = []
    fixes_applied = []
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\nFound {len(tables)} tables in database")
        
        # Check measurements table
        if 'measurements' in tables:
            print("\n" + "=" * 60)
            print("Checking 'measurements' table...")
            print("=" * 60)
            
            columns = {col['name']: col for col in inspector.get_columns('measurements')}
            column_names = list(columns.keys())
            print(f"Current columns: {', '.join(column_names)}")
            
            # Check for obsolete pd_number column
            if 'pd_number' in column_names:
                issues_found.append({
                    'table': 'measurements',
                    'issue': 'Obsolete column pd_number exists',
                    'action': 'DROP COLUMN'
                })
                print("\n[WARNING] Found obsolete 'pd_number' column")
                print("  This column is no longer used in the code.")
                print("  You can safely remove it with:")
                if 'postgresql' in settings.DATABASE_URL.lower():
                    print("    ALTER TABLE measurements DROP COLUMN pd_number;")
                else:
                    print("    Note: SQLite doesn't support DROP COLUMN easily.")
                    print("    You may need to recreate the table or use a migration tool.")
            
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
                    print(f"  [ERROR] Failed to add column: {e}")
                    print("  You may need to add it manually:")
                    if 'postgresql' in settings.DATABASE_URL.lower():
                        print("    ALTER TABLE measurements ADD COLUMN site_location VARCHAR;")
                    else:
                        print("    ALTER TABLE measurements ADD COLUMN site_location TEXT;")
            else:
                print("\n[OK] 'site_location' column exists")
        
        # Check measurement_entries table
        if 'measurement_entries' in tables:
            print("\n" + "=" * 60)
            print("Checking 'measurement_entries' table...")
            print("=" * 60)
            
            columns = {col['name']: col for col in inspector.get_columns('measurement_entries')}
            column_names = list(columns.keys())
            print(f"Current columns: {', '.join(column_names)}")
            
            # Check for obsolete pd_number column
            if 'pd_number' in column_names:
                issues_found.append({
                    'table': 'measurement_entries',
                    'issue': 'Obsolete column pd_number exists',
                    'action': 'DROP COLUMN'
                })
                print("\n[WARNING] Found obsolete 'pd_number' column")
                print("  This column is no longer used in the code.")
                print("  You can safely remove it with:")
                if 'postgresql' in settings.DATABASE_URL.lower():
                    print("    ALTER TABLE measurement_entries DROP COLUMN pd_number;")
                else:
                    print("    Note: SQLite doesn't support DROP COLUMN easily.")
        
        # Summary
        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)
        
        if fixes_applied:
            print(f"\n[OK] Applied {len(fixes_applied)} fixes:")
            for fix in fixes_applied:
                print(f"  - {fix}")
        
        if issues_found:
            print(f"\n[INFO] Found {len(issues_found)} issues that need attention:")
            for issue in issues_found:
                print(f"  - {issue['table']}: {issue['issue']}")
            print("\nThese are warnings - the application will work, but you may want to clean them up.")
        else:
            print("\n[OK] No issues found!")
        
        print("\n[OK] Database schema check completed")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Failed to check database schema: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\nStarting database schema check...\n")
    success = check_and_fix_schema()
    print("\n" + "=" * 60)
    if success:
        print("Check completed successfully!")
    else:
        print("Check completed with errors. Please review the output above.")
    print("=" * 60)
    sys.exit(0 if success else 1)
