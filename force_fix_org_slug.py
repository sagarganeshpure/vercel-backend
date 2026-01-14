"""
Force fix for organization_slug - tries multiple approaches
"""

import sys
import os

backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def force_fix():
    engine = create_engine(settings.DATABASE_URL)
    
    print("Checking database schema...")
    
    # First, check what columns actually exist
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    print(f"Current columns in users table: {', '.join(columns)}")
    
    if 'organization_slug' in columns:
        print("\n✓ Found organization_slug column - removing it...")
        
        # Get column info
        for col in inspector.get_columns('users'):
            if col['name'] == 'organization_slug':
                print(f"  Column info: nullable={col['nullable']}, type={col['type']}")
                break
        
        # Make nullable first
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ALTER COLUMN organization_slug DROP NOT NULL"))
                print("  ✓ Made nullable")
        except Exception as e:
            print(f"  Note (making nullable): {str(e)}")
        
        # Then remove
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users DROP COLUMN organization_slug"))
                print("  ✓ Removed column")
        except Exception as e:
            print(f"  Error removing: {str(e)}")
            raise
    else:
        print("\nColumn organization_slug does not exist - nothing to fix")
    
    # Verify
    inspector = inspect(engine)
    columns_after = [col['name'] for col in inspector.get_columns('users')]
    if 'organization_slug' not in columns_after:
        print("\nVerification: Column successfully removed!")
    else:
        print("\nWarning: Column still exists after removal attempt")

if __name__ == "__main__":
    force_fix()
