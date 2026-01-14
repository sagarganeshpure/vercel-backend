"""
Migration script to make title column nullable in production_papers table
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate_make_title_nullable():
    """Make title column nullable in production_papers table"""
    print("Starting migration to make title column nullable...")
    
    inspector = inspect(engine)
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if 'production_papers' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('production_papers')]
            
            if 'title' in columns:
                print("Making 'title' column nullable in production_papers...")
                if is_postgres:
                    # For PostgreSQL, we need to alter the column to drop NOT NULL constraint
                    conn.execute(text("ALTER TABLE production_papers ALTER COLUMN title DROP NOT NULL"))
                else:
                    # For SQLite, we need to recreate the table (more complex)
                    # For now, just try to alter it
                    conn.execute(text("ALTER TABLE production_papers ALTER COLUMN title DROP NOT NULL"))
                conn.commit()
                print("[OK] Made 'title' column nullable in production_papers")
            else:
                print("[WARNING] 'title' column does not exist in production_papers")
        else:
            print("ERROR: production_papers table does not exist. Please run init_db() first.")
            return
    
    print("\n[SUCCESS] Migration completed successfully!")

if __name__ == "__main__":
    migrate_make_title_nullable()





















