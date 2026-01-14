"""
Migration script to add product_type and product_sub_type columns to production_papers table
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine
from sqlalchemy import text

def migrate():
    """Add product_type and product_sub_type columns to production_papers table"""
    try:
        with engine.connect() as conn:
            is_postgresql = 'postgresql' in str(engine.url.drivername).lower()
            
            # Check if columns already exist
            if is_postgresql:
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='production_papers' 
                    AND column_name IN ('product_type', 'product_sub_type')
                """)
            else:  # SQLite
                # For SQLite, check by trying to select the columns
                try:
                    test_query = text("SELECT product_type, product_sub_type FROM production_papers LIMIT 1")
                    conn.execute(test_query)
                    print("Columns 'product_type' and 'product_sub_type' already exist in production_papers table")
                    return
                except:
                    pass  # Columns don't exist, continue to add them
            
            if is_postgresql:
                result = conn.execute(check_query)
                existing_columns = {row[0] for row in result.fetchall()}
            else:
                existing_columns = set()
            
            # Add product_type column if it doesn't exist
            if 'product_type' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS product_type VARCHAR
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN product_type VARCHAR
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'product_type' column to production_papers table")
            else:
                print("Column 'product_type' already exists, skipping")
            
            # Add product_sub_type column if it doesn't exist
            if 'product_sub_type' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS product_sub_type VARCHAR
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN product_sub_type VARCHAR
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'product_sub_type' column to production_papers table")
            else:
                print("Column 'product_sub_type' already exists, skipping")
            
    except Exception as e:
        error_msg = str(e).lower()
        # If column already exists, that's okay
        if 'already exists' in error_msg or 'duplicate' in error_msg or 'column' in error_msg and 'already' in error_msg:
            print("Column already exists, skipping migration")
        else:
            print(f"Error adding columns: {e}")
            raise

if __name__ == "__main__":
    migrate()

