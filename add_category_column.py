"""
Migration script to add the 'category' column to measurement_entries table.
Run this script once to fix the database schema.
"""
from app.db.database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_category_column():
    """Add category column to measurement_entries table if it doesn't exist"""
    try:
        with engine.connect() as conn:
            # Check if column exists (PostgreSQL)
            if 'postgresql' in str(engine.url):
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='measurement_entries' AND column_name='category'
                """)
                result = conn.execute(check_query)
                if result.fetchone():
                    logger.info("Column 'category' already exists in measurement_entries table")
                    return
                
                # Add the column
                alter_query = text("""
                    ALTER TABLE measurement_entries 
                    ADD COLUMN category VARCHAR
                """)
                conn.execute(alter_query)
                conn.commit()
                logger.info("Successfully added 'category' column to measurement_entries table")
            
            # SQLite
            elif 'sqlite' in str(engine.url):
                check_query = text("""
                    PRAGMA table_info(measurement_entries)
                """)
                result = conn.execute(check_query)
                columns = [row[1] for row in result.fetchall()]
                if 'category' in columns:
                    logger.info("Column 'category' already exists in measurement_entries table")
                    return
                
                # SQLite doesn't support ALTER TABLE ADD COLUMN easily, so we'll use a workaround
                # For SQLite, you may need to recreate the table
                logger.warning("SQLite detected. You may need to recreate the table or use a migration tool.")
                logger.info("For SQLite, consider using Alembic or recreating the database.")
            
                except Exception as e:
        logger.error(f"Error adding category column: {str(e)}")
                        raise

if __name__ == "__main__":
    print("Adding 'category' column to measurement_entries table...")
        add_category_column()
    print("Migration completed!")
