"""
Simple script to create designs table using SQLAlchemy
Works with both PostgreSQL and SQLite
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine, init_db
from app.db.base import Base
from sqlalchemy import inspect

def create_designs_table():
    """Create designs table if it doesn't exist"""
    try:
        print("Checking if designs table exists...")
        
        # Import Design model to register it with SQLAlchemy
        from app.db.models.user import Design
        
        # Check if table exists
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        if 'designs' not in existing_tables:
            print("Creating designs table...")
            # Create all tables (this will only create missing ones)
            Base.metadata.create_all(bind=engine, tables=[Design.__table__])
            print("[OK] designs table created successfully!")
        else:
            print("[OK] designs table already exists")
            
            # Check if image column exists
            columns = [col['name'] for col in inspector.get_columns('designs')]
            if 'image' not in columns:
                print("Adding image column to designs table...")
                from sqlalchemy import text
                with engine.connect() as conn:
                    if 'postgresql' in str(engine.url):
                        conn.execute(text("ALTER TABLE designs ADD COLUMN image TEXT"))
                    else:
                        # SQLite
                        conn.execute(text("ALTER TABLE designs ADD COLUMN image TEXT"))
                    conn.commit()
                print("[OK] image column added successfully!")
            else:
                print("[OK] image column already exists")
        
        print("\n[SUCCESS] Database setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Failed to create designs table: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_designs_table()
    sys.exit(0 if success else 1)

