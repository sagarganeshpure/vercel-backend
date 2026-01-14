"""
Migration script to add supervisor_type column to production_supervisors table
and supervisor_type column to production_tasks table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        print("Adding supervisor_type column to production_supervisors table...")
        
        # Check if column already exists
        check_column = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='production_supervisors' AND column_name='supervisor_type'
        """)
        result = db.execute(check_column).fetchone()
        
        if not result:
            # Add supervisor_type column to production_supervisors
            db.execute(text("""
                ALTER TABLE production_supervisors 
                ADD COLUMN supervisor_type VARCHAR(50) NOT NULL DEFAULT 'Frame'
            """))
            print("[OK] Added supervisor_type column to production_supervisors")
        else:
            print("[OK] supervisor_type column already exists in production_supervisors")
        
        # Check if column already exists in production_tasks
        check_task_column = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='production_tasks' AND column_name='supervisor_type'
        """)
        result_task = db.execute(check_task_column).fetchone()
        
        if not result_task:
            # Add supervisor_type column to production_tasks
            db.execute(text("""
                ALTER TABLE production_tasks 
                ADD COLUMN supervisor_type VARCHAR(50)
            """))
            print("[OK] Added supervisor_type column to production_tasks")
        else:
            print("[OK] supervisor_type column already exists in production_tasks")
        
        # Create index on supervisor_type for better query performance
        try:
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_production_supervisors_supervisor_type 
                ON production_supervisors(supervisor_type)
            """))
            print("[OK] Created index on supervisor_type in production_supervisors")
        except Exception as e:
            print(f"Index may already exist: {e}")
        
        try:
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_production_tasks_supervisor_type 
                ON production_tasks(supervisor_type)
            """))
            print("[OK] Created index on supervisor_type in production_tasks")
        except Exception as e:
            print(f"Index may already exist: {e}")
        
        db.commit()
        print("\nMigration completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"\nError during migration: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

