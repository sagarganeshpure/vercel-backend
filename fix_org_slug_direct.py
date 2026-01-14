"""
Direct fix for organization_slug column - makes it nullable then removes it.
This script doesn't check if column exists, it just tries to fix it.
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

def fix_organization_slug_direct():
    """Directly fix organization_slug column"""
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        logger.info("Connecting to database...")
        logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}")
        
        with engine.begin() as conn:
            db_type = settings.DATABASE_URL.split('://')[0] if '://' in settings.DATABASE_URL else 'sqlite'
            
            if 'postgresql' in db_type or 'postgres' in db_type:
                logger.info("Detected PostgreSQL database")
                
                # Step 1: Try to make column nullable (ignore error if already nullable or doesn't exist)
                try:
                    logger.info("Attempting to make column nullable...")
                    alter_query = text("ALTER TABLE users ALTER COLUMN organization_slug DROP NOT NULL")
                    conn.execute(alter_query)
                    logger.info("Column is now nullable")
                except Exception as e:
                    logger.info(f"Could not make nullable (may already be nullable or not exist): {str(e)}")
                
                # Step 2: Try to remove the column (ignore error if doesn't exist)
                try:
                    logger.info("Attempting to remove column...")
                    drop_query = text("ALTER TABLE users DROP COLUMN IF EXISTS organization_slug")
                    conn.execute(drop_query)
                    logger.info("Successfully removed 'organization_slug' column from users table")
                except Exception as e:
                    logger.warning(f"Could not remove column: {str(e)}")
                    # Try without IF EXISTS for older PostgreSQL versions
                    try:
                        drop_query = text("ALTER TABLE users DROP COLUMN organization_slug")
                        conn.execute(drop_query)
                        logger.info("Successfully removed 'organization_slug' column from users table")
                    except Exception as e2:
                        logger.error(f"Failed to remove column: {str(e2)}")
                        raise
            else:
                logger.warning("SQLite detected - manual migration required")
        
        logger.info("Database fix completed!")
        
    except Exception as e:
        logger.error(f"Error fixing organization_slug column: {str(e)}")
        raise

if __name__ == "__main__":
    print("Fixing 'organization_slug' column in users table...")
    print("This will make the column nullable (if needed) and then remove it.")
    fix_organization_slug_direct()
    print("Database fix completed!")
