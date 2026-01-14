"""
Migration script to add missing database columns
- measurements.site_location
- production_papers.po_number (if model expects it)
"""
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.core.config import settings
from app.db.database import engine

def migrate_database():
    """Add missing columns to database tables"""
    print("=" * 60)
    print("Database Migration: Add Missing Columns")
    print("=" * 60)
    
    fixes_applied = []
    errors = []
    
    try:
        inspector = inspect(engine)
        is_postgresql = 'postgresql' in settings.DATABASE_URL.lower()
        
        # Fix measurements table - add site_location
        if 'measurements' in inspector.get_table_names():
            print("\n[1/2] Checking 'measurements' table...")
            columns = {col['name']: col for col in inspector.get_columns('measurements')}
            
            if 'site_location' not in columns:
                print("  - Missing 'site_location' column")
                try:
                    with engine.connect() as conn:
                        if is_postgresql:
                            conn.execute(text("ALTER TABLE measurements ADD COLUMN IF NOT EXISTS site_location VARCHAR"))
                        else:  # SQLite
                            conn.execute(text("ALTER TABLE measurements ADD COLUMN site_location TEXT"))
                        conn.commit()
                    fixes_applied.append("Added 'site_location' to 'measurements' table")
                    print("  [OK] Added 'site_location' column")
                except Exception as e:
                    error_msg = f"Failed to add site_location: {e}"
                    errors.append(error_msg)
                    print(f"  [ERROR] {error_msg}")
            else:
                print("  [OK] 'site_location' column already exists")
        
        # Fix production_papers table - add po_number
        if 'production_papers' in inspector.get_table_names():
            print("\n[2/2] Checking 'production_papers' table...")
            columns = {col['name']: col for col in inspector.get_columns('production_papers')}
            
            if 'po_number' not in columns:
                print("  - Missing 'po_number' column")
                try:
                    with engine.connect() as conn:
                        if is_postgresql:
                            conn.execute(text("ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS po_number VARCHAR"))
                        else:  # SQLite
                            conn.execute(text("ALTER TABLE production_papers ADD COLUMN po_number TEXT"))
                        conn.commit()
                    fixes_applied.append("Added 'po_number' to 'production_papers' table")
                    print("  [OK] Added 'po_number' column")
                except Exception as e:
                    error_msg = f"Failed to add po_number: {e}"
                    errors.append(error_msg)
                    print(f"  [ERROR] {error_msg}")
            else:
                print("  [OK] 'po_number' column already exists")
        
        # Summary
        print("\n" + "=" * 60)
        print("Migration Summary")
        print("=" * 60)
        
        if fixes_applied:
            print(f"\n[OK] Applied {len(fixes_applied)} fixes:")
            for fix in fixes_applied:
                print(f"  ✓ {fix}")
        
        if errors:
            print(f"\n[ERROR] {len(errors)} errors occurred:")
            for error in errors:
                print(f"  ✗ {error}")
            return False
        
        if not fixes_applied:
            print("\n[OK] All columns already exist. No migration needed.")
        else:
            print("\n[OK] Migration completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\nStarting database migration...\n")
    success = migrate_database()
    print("\n" + "=" * 60)
    if success:
        print("Migration completed successfully!")
        print("You can now restart the server.")
    else:
        print("Migration completed with errors.")
        print("Please review the errors above and fix them manually.")
    print("=" * 60)
    sys.exit(0 if success else 1)
