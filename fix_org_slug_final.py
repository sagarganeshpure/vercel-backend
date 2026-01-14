"""
Final fix for organization_slug column.
Uses separate connections to avoid transaction issues.
"""

import sys
import os

backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_organization_slug():
    """Fix organization_slug column"""
    engine = create_engine(settings.DATABASE_URL)
    
    print("Connecting to database...")
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}")
    
    # Step 1: Make nullable (separate connection)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users ALTER COLUMN organization_slug DROP NOT NULL"))
            conn.commit()
            print("✓ Made column nullable")
    except Exception as e:
        if "does not exist" in str(e):
            print("Column already removed or doesn't exist")
        else:
            print(f"Note: {str(e)}")
    
    # Step 2: Remove column (separate connection)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE users DROP COLUMN organization_slug"))
            conn.commit()
            print("✓ Removed column")
    except Exception as e:
        if "does not exist" in str(e):
            print("Column already removed")
        else:
            print(f"Error: {str(e)}")
            raise
    
    print("\nDatabase fix completed!")

if __name__ == "__main__":
    fix_organization_slug()
