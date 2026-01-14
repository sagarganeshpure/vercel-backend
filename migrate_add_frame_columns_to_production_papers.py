"""
Migration script to add missing columns to production_papers table:
Frame fields: total_quantity, wall_type, rebate, sub_frame, construction, cover_moulding
Shutter fields: frontside_laminate, backside_laminate, grade, side_frame, filler, foam_bottom, frp_coating
"""
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text
from app.core.config import settings
from app.db.database import engine

def migrate_database():
    """Add missing columns to production_papers table"""
    print("=" * 60)
    print("Database Migration: Add Missing Production Paper Columns")
    print("=" * 60)
    
    fixes_applied = []
    errors = []
    
    try:
        inspector = inspect(engine)
        is_postgresql = 'postgresql' in settings.DATABASE_URL.lower()
        
        if 'production_papers' not in inspector.get_table_names():
            print("[ERROR] 'production_papers' table not found!")
            return False

        print("\nChecking 'production_papers' table columns...")
        columns = {col['name']: col for col in inspector.get_columns('production_papers')}
        
        # List of columns to add
        new_columns = [
            # Frame-specific fields
            'total_quantity',
            'wall_type',
            'rebate',
            'sub_frame',
            'construction',
            'cover_moulding',
            # Shutter-specific fields
            'frontside_laminate',
            'backside_laminate',
            'grade',
            'side_frame',
            'filler',
            'foam_bottom',
            'frp_coating'
        ]
        
        with engine.connect() as conn:
            for col_name in new_columns:
                if col_name not in columns:
                    print(f"  - Missing '{col_name}' column")
                    try:
                        if is_postgresql:
                            conn.execute(text(f"ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS {col_name} VARCHAR"))
                        else:  # SQLite
                            conn.execute(text(f"ALTER TABLE production_papers ADD COLUMN {col_name} TEXT"))
                        fixes_applied.append(f"Added '{col_name}' column")
                        print(f"  [OK] Added '{col_name}' column")
                    except Exception as e:
                        error_msg = f"Failed to add {col_name}: {e}"
                        errors.append(error_msg)
                        print(f"  [ERROR] {error_msg}")
                else:
                    print(f"  [OK] '{col_name}' column already exists")
            
            conn.commit()
        
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
