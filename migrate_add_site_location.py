"""
Migration script to add site_location column to measurements table
Run this to fix the missing column error
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate_add_site_location():
    """Add site_location column to measurements table"""
    print("Starting migration to add site_location column...")
    
    inspector = inspect(engine)
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if 'measurements' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('measurements')]
            
            # Add site_location column
            if 'site_location' not in columns:
                print("Adding 'site_location' column...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN site_location VARCHAR"))
                else:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN site_location VARCHAR"))
                conn.commit()
                print("[OK] Added 'site_location' column")
            else:
                print("[OK] 'site_location' column already exists")
        else:
            print("ERROR: measurements table does not exist. Please run init_db() first.")
            return
    
    print("\n[SUCCESS] Migration completed successfully!")

if __name__ == "__main__":
    migrate_add_site_location()

