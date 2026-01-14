"""
Check actual database schema for users table
"""

import sys
import os

backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def check_schema():
    engine = create_engine(settings.DATABASE_URL)
    
    print("Database URL:", settings.DATABASE_URL)
    print("\nChecking users table schema...")
    
    # Method 1: Using inspector
    inspector = inspect(engine)
    columns = inspector.get_columns('users')
    print("\nColumns (from inspector):")
    for col in columns:
        print(f"  - {col['name']}: nullable={col['nullable']}, type={col['type']}")
    
    # Method 2: Direct SQL query
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, is_nullable, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """))
        print("\nColumns (from information_schema):")
        for row in result:
            print(f"  - {row[0]}: nullable={row[1]}, type={row[2]}")

if __name__ == "__main__":
    check_schema()
