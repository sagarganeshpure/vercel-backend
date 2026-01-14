"""
Migration script to add serial number fields to users table
Run this to add serial_number_prefix and serial_number_counter columns
"""
from sqlalchemy import text
from app.db.database import engine, SessionLocal

def migrate_serial_numbers():
    """Add serial number fields to users table"""
    print("Starting serial number fields migration...")
    
    db = SessionLocal()
    try:
        with engine.connect() as conn:
            # Check and add serial_number_prefix column
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='serial_number_prefix'
            """))
            if result.fetchone() is None:
                print("Adding serial_number_prefix column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN serial_number_prefix VARCHAR"))
                conn.commit()
                print("[OK] Added serial_number_prefix column")
            else:
                print("[OK] serial_number_prefix column already exists")
            
            # Check and add serial_number_counter column
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='serial_number_counter'
            """))
            if result.fetchone() is None:
                print("Adding serial_number_counter column...")
                conn.execute(text("ALTER TABLE users ADD COLUMN serial_number_counter INTEGER DEFAULT 0 NOT NULL"))
                conn.commit()
                print("[OK] Added serial_number_counter column")
            else:
                print("[OK] serial_number_counter column already exists")
            
            # Create index on serial_number_prefix for faster lookups
            try:
                result = conn.execute(text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE tablename='users' AND indexname='ix_users_serial_number_prefix'
                """))
                if result.fetchone() is None:
                    print("Creating index on serial_number_prefix...")
                    conn.execute(text("CREATE INDEX ix_users_serial_number_prefix ON users(serial_number_prefix)"))
                    conn.commit()
                    print("[OK] Created index on serial_number_prefix")
                else:
                    print("[OK] Index on serial_number_prefix already exists")
            except Exception as e:
                print(f"[INFO] Could not create index (may not be PostgreSQL): {e}")
            
            print("\n[SUCCESS] Migration complete!")
            print("\nNote: Serial number prefixes must be manually assigned to Measurement Captain users by admin.")
            print("Use POST /admin/users/{user_id}/assign-serial-prefix endpoint to assign prefixes.")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_serial_numbers()


