import sys
import os
from sqlalchemy import text, inspect
from app.db.session import SessionLocal

def migrate():
    db = SessionLocal()
    try:
        print("Adding deletion_reason column to measurements table...")

        inspector = inspect(db.bind)
        columns = [col['name'] for col in inspector.get_columns('measurements')]

        if 'deletion_reason' not in columns:
            db.execute(text("ALTER TABLE measurements ADD COLUMN deletion_reason TEXT"))
            print("[OK] Added deletion_reason column")
        else:
            print("[OK] deletion_reason column already exists")

        db.commit()
        print("\nMigration completed successfully!")

    except Exception as e:
        db.rollback()
        print(f"\nError during migration: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    migrate()

