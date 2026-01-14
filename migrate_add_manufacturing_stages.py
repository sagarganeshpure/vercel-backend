"""
Migration script to create manufacturing_stages table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        print("Creating manufacturing_stages table...")
        
        # Check if table already exists
        check_table = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='manufacturing_stages'
        """)
        result = db.execute(check_table).fetchone()
        
        if not result:
            # Create manufacturing_stages table
            db.execute(text("""
                CREATE TABLE manufacturing_stages (
                    id SERIAL PRIMARY KEY,
                    stage_name VARCHAR NOT NULL UNIQUE,
                    description TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            print("[OK] Created manufacturing_stages table")
            
            # Create indexes
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_manufacturing_stages_stage_name 
                ON manufacturing_stages(stage_name)
            """))
            print("[OK] Created index on stage_name")
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_manufacturing_stages_created_by 
                ON manufacturing_stages(created_by)
            """))
            print("[OK] Created index on created_by")
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_manufacturing_stages_is_active 
                ON manufacturing_stages(is_active)
            """))
            print("[OK] Created index on is_active")
        else:
            print("[OK] manufacturing_stages table already exists")
        
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
    migrate()

