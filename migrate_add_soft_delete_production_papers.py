"""
Migration script to add soft delete columns to production_papers table
Run this to add is_deleted, deleted_at, and deletion_reason columns
"""
import sys
import os
from sqlalchemy import text
from app.db.session import SessionLocal

def migrate():
    db = SessionLocal()
    try:
        print("Adding soft delete columns to production_papers table...")

        # Check if is_deleted column exists
        check_is_deleted = text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'production_papers' AND column_name = 'is_deleted'
            );
        """)
        result = db.execute(check_is_deleted).scalar()

        if not result:
            # Add is_deleted column
            db.execute(text("""
                ALTER TABLE production_papers
                ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL;
            """))
            print("[OK] Added is_deleted column")

            # Create index on is_deleted
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_production_papers_is_deleted 
                ON production_papers(is_deleted);
            """))
            print("[OK] Created index on is_deleted")
        else:
            print("[OK] is_deleted column already exists")

        # Check if deleted_at column exists
        check_deleted_at = text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'production_papers' AND column_name = 'deleted_at'
            );
        """)
        result = db.execute(check_deleted_at).scalar()

        if not result:
            # Add deleted_at column
            db.execute(text("""
                ALTER TABLE production_papers
                ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;
            """))
            print("[OK] Added deleted_at column")
        else:
            print("[OK] deleted_at column already exists")

        # Check if deletion_reason column exists
        check_deletion_reason = text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'production_papers' AND column_name = 'deletion_reason'
            );
        """)
        result = db.execute(check_deletion_reason).scalar()

        if not result:
            # Add deletion_reason column
            db.execute(text("""
                ALTER TABLE production_papers
                ADD COLUMN deletion_reason TEXT;
            """))
            print("[OK] Added deletion_reason column")
        else:
            print("[OK] deletion_reason column already exists")

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

