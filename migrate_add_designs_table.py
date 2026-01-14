"""
Migration script to create designs table
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        print("Creating designs table...")
        
        # Check if table already exists
        check_table = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='designs'
        """)
        result = db.execute(check_table).fetchone()
        
        if not result:
            # Create designs table
            db.execute(text("""
                CREATE TABLE designs (
                    id SERIAL PRIMARY KEY,
                    design_name VARCHAR NOT NULL UNIQUE,
                    design_code VARCHAR NOT NULL UNIQUE,
                    description TEXT,
                    image TEXT,
                    product_category VARCHAR NOT NULL DEFAULT 'Shutter',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
            """))
            print("[OK] Created designs table")
            
            # Create indexes
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_designs_design_name 
                ON designs(design_name)
            """))
            print("[OK] Created index on design_name")
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_designs_design_code 
                ON designs(design_code)
            """))
            print("[OK] Created index on design_code")
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_designs_created_by 
                ON designs(created_by)
            """))
            print("[OK] Created index on created_by")
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_designs_product_category 
                ON designs(product_category)
            """))
            print("[OK] Created index on product_category")
            
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_designs_is_active 
                ON designs(is_active)
            """))
            print("[OK] Created index on is_active")
        else:
            print("[OK] designs table already exists")
            # Check if image column exists, if not add it
            check_image_column = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='designs' AND column_name='image'
            """)
            image_result = db.execute(check_image_column).fetchone()
            
            if not image_result:
                print("Adding image column to designs table...")
                db.execute(text("""
                    ALTER TABLE designs ADD COLUMN image TEXT
                """))
                print("[OK] Added image column")
            else:
                print("[OK] image column already exists")
        
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

