"""
Migration script to add expected_dispatch_date and production_start_date columns to production_papers table
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine
from sqlalchemy import text

def migrate():
    """Add expected_dispatch_date and production_start_date columns to production_papers table"""
    try:
        with engine.connect() as conn:
            is_postgresql = 'postgresql' in str(engine.url.drivername).lower()
            
            # Check if columns already exist
            if is_postgresql:
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='production_papers' 
                    AND column_name IN ('expected_dispatch_date', 'production_start_date')
                """)
            else:  # SQLite
                # For SQLite, check by trying to select the columns
                try:
                    test_query = text("SELECT expected_dispatch_date, production_start_date FROM production_papers LIMIT 1")
                    conn.execute(test_query)
                    print("Columns 'expected_dispatch_date' and 'production_start_date' already exist in production_papers table")
                    return
                except:
                    pass  # Columns don't exist, continue to add them
            
            if is_postgresql:
                result = conn.execute(check_query)
                existing_columns = {row[0] for row in result.fetchall()}
            else:
                existing_columns = set()
            
            # Add expected_dispatch_date column if it doesn't exist
            if 'expected_dispatch_date' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS expected_dispatch_date DATE
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN expected_dispatch_date DATE
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'expected_dispatch_date' column to production_papers table")
            else:
                print("Column 'expected_dispatch_date' already exists, skipping")
            
            # Add production_start_date column if it doesn't exist
            if 'production_start_date' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS production_start_date DATE
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN production_start_date DATE
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'production_start_date' column to production_papers table")
            else:
                print("Column 'production_start_date' already exists, skipping")
            
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

