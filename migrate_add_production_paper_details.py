"""
Migration script to add new detail columns to production_papers table
Adds: site_name, site_location, area, concept, thickness, design, gel_colour, laminate, remark
Run this to add the new fields for production paper details
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate_add_production_paper_details():
    """Add new detail columns to production_papers table"""
    print("Starting migration to add production paper detail columns...")
    
    inspector = inspect(engine)
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if 'production_papers' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('production_papers')]
            
            # Define new columns to add
            new_columns = {
                'site_name': 'VARCHAR',
                'site_location': 'VARCHAR',
                'area': 'VARCHAR',
                'concept': 'VARCHAR',
                'thickness': 'VARCHAR',
                'design': 'VARCHAR',
                'gel_colour': 'VARCHAR',
                'laminate': 'VARCHAR',
                'remark': 'TEXT'
            }
            
            # Add each column if it doesn't exist
            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    print(f"Adding '{col_name}' column to production_papers...")
                    if is_postgres:
                        conn.execute(text(f"ALTER TABLE production_papers ADD COLUMN {col_name} {col_type}"))
                    else:
                        conn.execute(text(f"ALTER TABLE production_papers ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    print(f"[OK] Added '{col_name}' column to production_papers")
                else:
                    print(f"[OK] '{col_name}' column already exists in production_papers")
        else:
            print("ERROR: production_papers table does not exist. Please run init_db() first.")
            return
    
    print("\n[SUCCESS] Migration completed successfully!")

if __name__ == "__main__":
    migrate_add_production_paper_details()





















