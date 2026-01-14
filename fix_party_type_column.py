"""
Fix script to ensure party_type column has proper constraints
"""
from sqlalchemy import text
from app.db.database import engine

def fix_party_type_column():
    """Ensure party_type column has NOT NULL and DEFAULT constraints"""
    print("Fixing party_type column constraints...")
    
    with engine.connect() as conn:
        try:
            # First, update any NULL values to 'Builder'
            print("Updating NULL party_type values to 'Builder'...")
            conn.execute(text("UPDATE parties SET party_type = 'Builder' WHERE party_type IS NULL"))
            conn.commit()
            print("[OK] Updated NULL values")
            
            # Set default value for the column
            print("Setting default value for party_type...")
            conn.execute(text("ALTER TABLE parties ALTER COLUMN party_type SET DEFAULT 'Builder'"))
            conn.commit()
            print("[OK] Set default value")
            
            # Set NOT NULL constraint
            print("Setting NOT NULL constraint...")
            conn.execute(text("ALTER TABLE parties ALTER COLUMN party_type SET NOT NULL"))
            conn.commit()
            print("[OK] Set NOT NULL constraint")
            
            print("\n[SUCCESS] party_type column fixed successfully!")
            
        except Exception as e:
            print(f"[ERROR] Failed to fix party_type column: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    fix_party_type_column()











