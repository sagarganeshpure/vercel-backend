"""
Migration script to add material availability columns to production_papers table
"""
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.database import engine
from sqlalchemy import text

def migrate():
    """Add material availability columns to production_papers table"""
    try:
        with engine.connect() as conn:
            is_postgresql = 'postgresql' in str(engine.url.drivername).lower()
            
            # Check if columns already exist
            if is_postgresql:
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='production_papers' 
                    AND column_name IN ('shutter_available', 'laminate_available', 'frame_material_available', 'raw_material_check_date')
                """)
            else:  # SQLite
                # For SQLite, check by trying to select the columns
                try:
                    test_query = text("SELECT shutter_available, laminate_available, frame_material_available, raw_material_check_date FROM production_papers LIMIT 1")
                    conn.execute(test_query)
                    print("Material availability columns already exist in production_papers table")
                    return
                except:
                    pass  # Columns don't exist, continue to add them
            
            if is_postgresql:
                result = conn.execute(check_query)
                existing_columns = {row[0] for row in result.fetchall()}
            else:
                existing_columns = set()
            
            # Add shutter_available column if it doesn't exist
            if 'shutter_available' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS shutter_available BOOLEAN DEFAULT FALSE
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN shutter_available BOOLEAN DEFAULT 0
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'shutter_available' column to production_papers table")
            else:
                print("Column 'shutter_available' already exists, skipping")
            
            # Add laminate_available column if it doesn't exist
            if 'laminate_available' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS laminate_available BOOLEAN DEFAULT FALSE
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN laminate_available BOOLEAN DEFAULT 0
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'laminate_available' column to production_papers table")
            else:
                print("Column 'laminate_available' already exists, skipping")
            
            # Add frame_material_available column if it doesn't exist
            if 'frame_material_available' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS frame_material_available BOOLEAN DEFAULT FALSE
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN frame_material_available BOOLEAN DEFAULT 0
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'frame_material_available' column to production_papers table")
            else:
                print("Column 'frame_material_available' already exists, skipping")
            
            # Add raw_material_check_date column if it doesn't exist
            if 'raw_material_check_date' not in existing_columns:
                if is_postgresql:
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN IF NOT EXISTS raw_material_check_date TIMESTAMP WITH TIME ZONE
                    """)
                else:  # SQLite
                    alter_query = text("""
                        ALTER TABLE production_papers 
                        ADD COLUMN raw_material_check_date TIMESTAMP
                    """)
                conn.execute(alter_query)
                conn.commit()
                print("Successfully added 'raw_material_check_date' column to production_papers table")
            else:
                print("Column 'raw_material_check_date' already exists, skipping")
            
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

