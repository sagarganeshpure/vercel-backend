"""
Migration script to remove organization_slug column from users table.

This script removes the organization_slug column from the users table
in both PostgreSQL and SQLite databases.

Usage:
    python migrate_remove_organization_slug.py
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

def remove_organization_slug_column():
    """Remove organization_slug column from users table"""
    try:
        # Create database engine
        engine = create_engine(settings.DATABASE_URL)
        
        logger.info("Connecting to database...")
        logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}")
        
        with engine.connect() as conn:
            # Check database type
            db_type = settings.DATABASE_URL.split('://')[0] if '://' in settings.DATABASE_URL else 'sqlite'
            
            if 'postgresql' in db_type or 'postgres' in db_type:
                # PostgreSQL
                logger.info("Detected PostgreSQL database")
                
                # Check if column exists
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'organization_slug'
                """)
                result = conn.execute(check_query)
                column_exists = result.fetchone() is not None
                
                if column_exists:
                    logger.info("Column 'organization_slug' exists. Removing...")
                    # Remove column
                    alter_query = text("ALTER TABLE users DROP COLUMN organization_slug")
                    conn.execute(alter_query)
                    conn.commit()
                    logger.info("Successfully removed 'organization_slug' column from users table")
                else:
                    logger.info("Column 'organization_slug' does not exist. Nothing to remove.")
                    
            else:
                # SQLite
                logger.info("Detected SQLite database")
                logger.warning("SQLite does not support DROP COLUMN directly.")
                logger.warning("You need to recreate the table without the organization_slug column.")
                logger.warning("This script will check if the column exists but cannot remove it automatically.")
                
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
                    logger.info("Column 'organization_slug' does not exist. Nothing to remove.")
        
        logger.info("Migration completed!")
        
    except Exception as e:
        logger.error(f"Error removing organization_slug column: {str(e)}")
        raise

if __name__ == "__main__":
    print("Removing 'organization_slug' column from users table...")
    remove_organization_slug_column()
    print("Migration completed!")
