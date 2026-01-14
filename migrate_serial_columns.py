"""
Migration script to add serial_number_prefix and serial_number_counter columns to users table
Run this if you have an existing database
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate_serial_columns():
    """Add missing serial number columns to existing database"""
    print("Starting database migration for serial number columns...")
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        if 'users' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            # Add serial_number_prefix column
            if 'serial_number_prefix' not in columns:
                print("Adding 'serial_number_prefix' column to users table...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE users ADD COLUMN serial_number_prefix VARCHAR"))
                else:
                    conn.execute(text("ALTER TABLE users ADD COLUMN serial_number_prefix VARCHAR"))
                conn.commit()
                print("[OK] Added 'serial_number_prefix' column")
            else:
                print("[OK] 'serial_number_prefix' column already exists")
            
            # Add serial_number_counter column
            if 'serial_number_counter' not in columns:
                print("Adding 'serial_number_counter' column to users table...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE users ADD COLUMN serial_number_counter INTEGER DEFAULT 0 NOT NULL"))
                else:
                    conn.execute(text("ALTER TABLE users ADD COLUMN serial_number_counter INTEGER DEFAULT 0 NOT NULL"))
                conn.commit()
                print("[OK] Added 'serial_number_counter' column")
            else:
                print("[OK] 'serial_number_counter' column already exists")
            
            # Create index on serial_number_prefix if it doesn't exist
            if is_postgres:
                try:
                    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_serial_number_prefix ON users(serial_number_prefix)"))
                    conn.commit()
                    print("[OK] Created index on serial_number_prefix")
                except Exception as e:
                    print(f"[INFO] Index may already exist: {e}")
        else:
            print("[ERROR] 'users' table does not exist")
            return
    
    print("\n[SUCCESS] Serial number columns migration completed successfully!")

if __name__ == "__main__":
    migrate_serial_columns()

