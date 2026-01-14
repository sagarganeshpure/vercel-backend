"""
Migration script to add soft delete columns to measurements table
Run this to add is_deleted and deleted_at columns
"""
import sys
import os
from sqlalchemy import text
from app.db.session import SessionLocal

def migrate():
    db = SessionLocal()
    try:
        print("Adding soft delete columns to measurements table...")

        # Check if columns already exist
        check_is_deleted = text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'measurements' AND column_name = 'is_deleted'
            );
        """)
        result = db.execute(check_is_deleted).scalar()

        if not result:
            # Add is_deleted column
            db.execute(text("""
                ALTER TABLE measurements
                ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL;
            """))
            print("[OK] Added is_deleted column")

            # Create index on is_deleted
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_measurements_is_deleted 
                ON measurements(is_deleted);
            """))
            print("[OK] Created index on is_deleted")
        else:
            print("[OK] is_deleted column already exists")

        # Check if deleted_at column exists
        check_deleted_at = text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'measurements' AND column_name = 'deleted_at'
            );
        """)
        result = db.execute(check_deleted_at).scalar()

        if not result:
            # Add deleted_at column
            db.execute(text("""
                ALTER TABLE measurements
                ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
            """))
            print("[OK] Added deleted_at column")
        else:
            print("[OK] deleted_at column already exists")

        db.commit()
        print("\nMigration completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"\nError during migration: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Add parent directory to path to allow imports
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    migrate()

