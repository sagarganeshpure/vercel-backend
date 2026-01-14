"""
Fix organization_slug column in database.

This script:
1. First makes the column nullable (if it exists and is NOT NULL)
2. Then removes the column completely

This handles the case where the column still exists in the database
but the code no longer uses it.
"""

import sys
import os

# Add backend directory to path for imports
backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from sqlalchemy import create_engine, text
from app.core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_organization_slug_column():
    """Fix organization_slug column - make nullable then remove"""
    try:
        # Create database engine
        engine = create_engine(settings.DATABASE_URL)
        
        logger.info("Connecting to database...")
        logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}")
        
        with engine.begin() as conn:  # Use begin() for automatic transaction management
            # Check database type
            db_type = settings.DATABASE_URL.split('://')[0] if '://' in settings.DATABASE_URL else 'sqlite'
            
            if 'postgresql' in db_type or 'postgres' in db_type:
                # PostgreSQL
                logger.info("Detected PostgreSQL database")
                
                # Step 1: Check if column exists
                check_query = text("""
                    SELECT column_name, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'organization_slug'
                """)
                result = conn.execute(check_query)
                column_info = result.fetchone()
                
                if column_info:
                    column_name, is_nullable = column_info
                    logger.info(f"Column 'organization_slug' exists. Nullable: {is_nullable}")
                    
                    # Step 2: If NOT NULL, make it nullable first
                    if is_nullable == 'NO':
                        logger.info("Making column nullable...")
                        alter_query = text("ALTER TABLE users ALTER COLUMN organization_slug DROP NOT NULL")
                        conn.execute(alter_query)
                        logger.info("Column is now nullable")
                    
                    # Step 3: Remove the column
                    logger.info("Removing 'organization_slug' column...")
                    drop_query = text("ALTER TABLE users DROP COLUMN organization_slug")
                    conn.execute(drop_query)
                    logger.info("Successfully removed 'organization_slug' column from users table")
                else:
                    logger.info("Column 'organization_slug' does not exist. Nothing to fix.")
                    
            else:
                # SQLite
                logger.info("Detected SQLite database")
                logger.warning("SQLite does not support DROP COLUMN directly.")
                logger.warning("You need to recreate the table without the organization_slug column.")
                logger.warning("Consider using Alembic for SQLite migrations.")
                
                # Check if column exists
                check_query = text("PRAGMA table_info(users)")
                result = conn.execute(check_query)
                columns = [row[1] for row in result.fetchall()]
                
                if 'organization_slug' in columns:
                    logger.warning("Column 'organization_slug' exists in SQLite table.")
                    logger.warning("To remove it, you need to:")
                    logger.warning("1. Create a new table without organization_slug")
                    logger.warning("2. Copy data from old table to new table")
                    logger.warning("3. Drop old table and rename new table")
                    logger.warning("Consider using Alembic for SQLite migrations.")
                else:
                    logger.info("Column 'organization_slug' does not exist. Nothing to fix.")
        
        logger.info("Database fix completed!")
        
    except Exception as e:
        logger.error(f"Error fixing organization_slug column: {str(e)}")
        raise

if __name__ == "__main__":
    print("Fixing 'organization_slug' column in users table...")
    print("This will make the column nullable (if needed) and then remove it.")
    fix_organization_slug_column()
    print("Database fix completed!")





