"""
Script to check and fix database schema issues
This script checks for missing columns and removes obsolete columns
"""
import sys
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.core.config import settings
from app.db.database import engine

def check_and_fix_schema():
    """Check database schema and fix any issues"""
    print("Checking database schema...")
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'measurements' in tables:
            print("\nChecking 'measurements' table...")
            columns = [col['name'] for col in inspector.get_columns('measurements')]
            print(f"Current columns: {', '.join(columns)}")
        
            # Check if pd_number column exists (should be removed)
            if 'pd_number' in columns:
                print("\n[WARNING] Found obsolete 'pd_number' column in 'measurements' table")
                print("This column should be removed. You can remove it manually with:")
                print("  ALTER TABLE measurements DROP COLUMN pd_number;")
                print("Or it will be ignored by the application.")
            
            # Check if site_location column exists (should be added)
            if 'site_location' not in columns:
                print("\n[INFO] 'site_location' column not found in 'measurements' table")
                print("Adding 'site_location' column...")
                try:
                    with engine.connect() as conn:
                        if 'postgresql' in settings.DATABASE_URL.lower():
                            conn.execute(text("ALTER TABLE measurements ADD COLUMN site_location VARCHAR"))
                        else:  # SQLite
                            conn.execute(text("ALTER TABLE measurements ADD COLUMN site_location TEXT"))
                        conn.commit()
                    print("[OK] 'site_location' column added successfully")
                except Exception as e:
                    print(f"[ERROR] Failed to add 'site_location' column: {e}")
            else:
                print("[OK] 'site_location' column exists")
        
        if 'measurement_entries' in tables:
            print("\nChecking 'measurement_entries' table...")
            columns = [col['name'] for col in inspector.get_columns('measurement_entries')]
            print(f"Current columns: {', '.join(columns)}")
            
            # Check if pd_number column exists (should be removed)
            if 'pd_number' in columns:
                print("\n[WARNING] Found obsolete 'pd_number' column in 'measurement_entries' table")
                print("This column should be removed. You can remove it manually with:")
                print("  ALTER TABLE measurement_entries DROP COLUMN pd_number;")
                print("Or it will be ignored by the application.")
        
        print("\n[OK] Database schema check completed")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Failed to check database schema: {e}")
        return False

if __name__ == "__main__":
    success = check_and_fix_schema()
    sys.exit(0 if success else 1)
