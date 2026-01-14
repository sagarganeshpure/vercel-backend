"""
Migration script to add selected_measurement_items column to production_papers table
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine
from sqlalchemy import text

def migrate():
    """Add selected_measurement_items column to production_papers table"""
    try:
        with engine.connect() as conn:
            is_postgresql = 'postgresql' in str(engine.url.drivername).lower()
            
            # Check if column already exists
            if is_postgresql:
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='production_papers' 
                    AND column_name='selected_measurement_items'
                """)
                result = conn.execute(check_query)
                existing_columns = {row[0] for row in result.fetchall()}
            else:  # SQLite
                # For SQLite, check by trying to select the column
                try:
                    test_query = text("SELECT selected_measurement_items FROM production_papers LIMIT 1")
                    conn.execute(test_query)
                    print("Column 'selected_measurement_items' already exists in production_papers table")
                    return
                except:
                    existing_columns = set()  # Column doesn't exist, continue to add it
            
            # Add selected_measurement_items column if it doesn't exist
            if 'selected_measurement_items' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS selected_measurement_items TEXT
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN selected_measurement_items TEXT
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'selected_measurement_items' column to production_papers table")
            else:
                print("Column 'selected_measurement_items' already exists, skipping")
            
    except Exception as e:
        error_msg = str(e).lower()
        # If column already exists, that's okay
        if 'already exists' in error_msg or 'duplicate' in error_msg or 'column' in error_msg and 'already' in error_msg:
            print("Column already exists, skipping migration")
        else:
            print(f"Error adding column: {e}")
            raise

if __name__ == "__main__":
    migrate()





