"""
Migration script to add remarks, title, and description columns to production_papers table
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine
from sqlalchemy import text

def migrate():
    """Add remarks, title, and description columns to production_papers table"""
    try:
        with engine.connect() as conn:
            is_postgresql = 'postgresql' in str(engine.url.drivername).lower()
            
            # Check if columns already exist
            if is_postgresql:
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='production_papers' 
                    AND column_name IN ('remarks', 'title', 'description')
                """)
            else:  # SQLite
                # For SQLite, check by trying to select the columns
                try:
                    test_query = text("SELECT remarks, title, description FROM production_papers LIMIT 1")
                    conn.execute(test_query)
                    print("Columns 'remarks', 'title', and 'description' already exist in production_papers table")
                    return
                except:
                    pass  # Columns don't exist, continue to add them
            
            if is_postgresql:
                result = conn.execute(check_query)
                existing_columns = {row[0] for row in result.fetchall()}
            else:
                existing_columns = set()
            
            # Add remarks column if it doesn't exist
            if 'remarks' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS remarks TEXT
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN remarks TEXT
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'remarks' column to production_papers table")
            else:
                print("Column 'remarks' already exists, skipping")
            
            # Add title column if it doesn't exist
            if 'title' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS title VARCHAR
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN title VARCHAR
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'title' column to production_papers table")
            else:
                print("Column 'title' already exists, skipping")
            
            # Add description column if it doesn't exist
            if 'description' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS description TEXT
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN description TEXT
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'description' column to production_papers table")
            else:
                print("Column 'description' already exists, skipping")
            
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

