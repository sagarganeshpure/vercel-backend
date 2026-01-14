"""
Fix measurements table - make old columns nullable
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def fix_measurements_nullable():
    """Make old measurement columns nullable"""
    print("Fixing measurements table - making old columns nullable...")
    
    inspector = inspect(engine)
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if 'measurements' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('measurements')]
            
            # Make name nullable
            if 'name' in columns:
                print("Making 'name' column nullable...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ALTER COLUMN name DROP NOT NULL"))
                else:
                    conn.execute(text("ALTER TABLE measurements ALTER COLUMN name DROP NOT NULL"))
                conn.commit()
                print("[OK] Made 'name' column nullable")
            
            # Make value nullable
            if 'value' in columns:
                print("Making 'value' column nullable...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ALTER COLUMN value DROP NOT NULL"))
                else:
                    conn.execute(text("ALTER TABLE measurements ALTER COLUMN value DROP NOT NULL"))
                conn.commit()
                print("[OK] Made 'value' column nullable")
            
            # Make unit nullable (if it exists and is not nullable)
            if 'unit' in columns:
                print("Making 'unit' column nullable...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ALTER COLUMN unit DROP NOT NULL"))
                else:
                    conn.execute(text("ALTER TABLE measurements ALTER COLUMN unit DROP NOT NULL"))
                conn.commit()
                print("[OK] Made 'unit' column nullable")
            
            # Make description nullable (if it exists and is not nullable)
            if 'description' in columns:
                print("Making 'description' column nullable...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ALTER COLUMN description DROP NOT NULL"))
                else:
                    conn.execute(text("ALTER TABLE measurements ALTER COLUMN description DROP NOT NULL"))
                conn.commit()
                print("[OK] Made 'description' column nullable")
        else:
            print("ERROR: measurements table does not exist.")
            return
    
    print("\n[SUCCESS] Measurements table fixed successfully!")

if __name__ == "__main__":
    fix_measurements_nullable()

