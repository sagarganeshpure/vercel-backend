"""
Migration script to add party_name column to production_papers table
Run this to fix the missing column error
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate_add_party_name():
    """Add party_name column to production_papers table"""
    print("Starting migration to add party_name column to production_papers...")
    
    inspector = inspect(engine)
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if 'production_papers' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('production_papers')]
            
            # Add party_name column
            if 'party_name' not in columns:
                print("Adding 'party_name' column to production_papers...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE production_papers ADD COLUMN party_name VARCHAR"))
                else:
                    conn.execute(text("ALTER TABLE production_papers ADD COLUMN party_name VARCHAR"))
                conn.commit()
                print("[OK] Added 'party_name' column to production_papers")
            else:
                print("[OK] 'party_name' column already exists in production_papers")
        else:
            print("ERROR: production_papers table does not exist. Please run init_db() first.")
            return
    
    print("\n[SUCCESS] Migration completed successfully!")

if __name__ == "__main__":
    migrate_add_party_name()

