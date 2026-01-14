"""
Migration script to add order_type column to production_papers table
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine
from sqlalchemy import text

def migrate():
    """Add order_type column to production_papers table"""
    try:
        with engine.connect() as conn:
            is_postgresql = 'postgresql' in str(engine.url.drivername).lower()
            
            # Check if column already exists
            if is_postgresql:
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='production_papers' AND column_name='order_type'
                """)
            else:  # SQLite
                # For SQLite, check by trying to select the column
                try:
                    test_query = text("SELECT order_type FROM production_papers LIMIT 1")
                    conn.execute(test_query)
                    print("Column 'order_type' already exists in production_papers table")
                    return
                except:
                    pass  # Column doesn't exist, continue to add it
            
            if is_postgresql:
                result = conn.execute(check_query)
                exists = result.fetchone()
                if exists:
                    print("Column 'order_type' already exists in production_papers table")
                    return
            
            # Add the column
            if is_postgresql:
                # For PostgreSQL, add as nullable first, then update, then make NOT NULL
                alter_query1 = text("""
                    ALTER TABLE production_papers 
                    ADD COLUMN IF NOT EXISTS order_type VARCHAR
                """)
                conn.execute(alter_query1)
                conn.commit()
                
                # Update existing rows
                update_query = text("""
                    UPDATE production_papers 
                    SET order_type = 'Regular' 
                    WHERE order_type IS NULL
                """)
                conn.execute(update_query)
                conn.commit()
                
                # Make it NOT NULL with default
                alter_query2 = text("""
                    ALTER TABLE production_papers 
                    ALTER COLUMN order_type SET DEFAULT 'Regular',
                    ALTER COLUMN order_type SET NOT NULL
                """)
                conn.execute(alter_query2)
                conn.commit()
            else:  # SQLite
                alter_query = text("""
                    ALTER TABLE production_papers 
                    ADD COLUMN order_type VARCHAR DEFAULT 'Regular'
                """)
                conn.execute(alter_query)
                conn.commit()
                
                # Update existing rows
                update_query = text("""
                    UPDATE production_papers 
                    SET order_type = 'Regular' 
                    WHERE order_type IS NULL
                """)
                conn.execute(update_query)
                conn.commit()
            
            print("Successfully added 'order_type' column to production_papers table")
            
    except Exception as e:
        error_msg = str(e).lower()
        # If column already exists, that's okay
        if 'already exists' in error_msg or 'duplicate' in error_msg or 'column' in error_msg and 'already' in error_msg:
            print("Column already exists, skipping migration")
        else:
            print(f"Error adding order_type column: {e}")
            raise

if __name__ == "__main__":
    migrate()

