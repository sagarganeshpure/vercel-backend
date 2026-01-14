"""
Migration script to add project_site_name column to production_papers table
Run this to fix the missing column error
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate_add_project_site_name():
    """Add project_site_name column to production_papers table"""
    print("Starting migration to add project_site_name column to production_papers...")
    
    inspector = inspect(engine)
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if 'production_papers' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('production_papers')]
            
            # Add project_site_name column
            if 'project_site_name' not in columns:
                print("Adding 'project_site_name' column to production_papers...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE production_papers ADD COLUMN project_site_name VARCHAR"))
                else:
                    conn.execute(text("ALTER TABLE production_papers ADD COLUMN project_site_name VARCHAR"))
                conn.commit()
                print("[OK] Added 'project_site_name' column to production_papers")
            else:
                print("[OK] 'project_site_name' column already exists in production_papers")
        else:
            print("ERROR: production_papers table does not exist. Please run init_db() first.")
            return
    
    print("\n[SUCCESS] Migration completed successfully!")

if __name__ == "__main__":
    migrate_add_project_site_name()

