"""
Migration script to update measurements table with new columns
Run this to add the new measurement fields
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate_measurements():
    """Add new columns to measurements table"""
    print("Starting measurements table migration...")
    
    inspector = inspect(engine)
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    with engine.connect() as conn:
        if 'measurements' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('measurements')]
            
            # Add measurement_type column
            if 'measurement_type' not in columns:
                print("Adding 'measurement_type' column...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN measurement_type VARCHAR"))
                else:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN measurement_type VARCHAR"))
                conn.commit()
                print("[OK] Added 'measurement_type' column")
            else:
                print("[OK] 'measurement_type' column already exists")
            
            # Add measurement_number column
            if 'measurement_number' not in columns:
                print("Adding 'measurement_number' column...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN measurement_number VARCHAR"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_measurements_number ON measurements(measurement_number)"))
                else:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN measurement_number VARCHAR"))
                    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_measurements_number ON measurements(measurement_number)"))
                conn.commit()
                print("[OK] Added 'measurement_number' column")
            else:
                print("[OK] 'measurement_number' column already exists")
            
            # Add party_id column
            if 'party_id' not in columns:
                print("Adding 'party_id' column...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN party_id INTEGER"))
                    conn.execute(text("ALTER TABLE measurements ADD CONSTRAINT fk_measurements_party FOREIGN KEY (party_id) REFERENCES parties(id)"))
                else:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN party_id INTEGER"))
                conn.commit()
                print("[OK] Added 'party_id' column")
            else:
                print("[OK] 'party_id' column already exists")
            
            # Add party_name column
            if 'party_name' not in columns:
                print("Adding 'party_name' column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN party_name VARCHAR"))
                conn.commit()
                print("[OK] Added 'party_name' column")
            else:
                print("[OK] 'party_name' column already exists")
            
            # Add pd_number column
            if 'pd_number' not in columns:
                print("Adding 'pd_number' column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN pd_number VARCHAR"))
                conn.commit()
                print("[OK] Added 'pd_number' column")
            else:
                print("[OK] 'pd_number' column already exists")
            
            # Add thickness column
            if 'thickness' not in columns:
                print("Adding 'thickness' column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN thickness VARCHAR"))
                conn.commit()
                print("[OK] Added 'thickness' column")
            else:
                print("[OK] 'thickness' column already exists")
            
            # Add measurement_date column
            if 'measurement_date' not in columns:
                print("Adding 'measurement_date' column...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN measurement_date TIMESTAMP WITH TIME ZONE"))
                else:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN measurement_date TIMESTAMP"))
                conn.commit()
                print("[OK] Added 'measurement_date' column")
            else:
                print("[OK] 'measurement_date' column already exists")
            
            # Add items column (JSON)
            if 'items' not in columns:
                print("Adding 'items' column (JSON)...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN items JSON"))
                else:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN items TEXT"))
                conn.commit()
                print("[OK] Added 'items' column")
            else:
                print("[OK] 'items' column already exists")
            
            # Add notes column
            if 'notes' not in columns:
                print("Adding 'notes' column...")
                if is_postgres:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN notes TEXT"))
                else:
                    conn.execute(text("ALTER TABLE measurements ADD COLUMN notes TEXT"))
                conn.commit()
                print("[OK] Added 'notes' column")
            else:
                print("[OK] 'notes' column already exists")
            
            # Remove old columns if they exist (optional - comment out if you want to keep them)
            # if 'name' in columns:
            #     print("Removing old 'name' column...")
            #     conn.execute(text("ALTER TABLE measurements DROP COLUMN name"))
            #     conn.commit()
            # if 'value' in columns:
            #     print("Removing old 'value' column...")
            #     conn.execute(text("ALTER TABLE measurements DROP COLUMN value"))
            #     conn.commit()
            # if 'unit' in columns:
            #     print("Removing old 'unit' column...")
            #     conn.execute(text("ALTER TABLE measurements DROP COLUMN unit"))
            #     conn.commit()
        else:
            print("ERROR: measurements table does not exist. Please run init_db.py first.")
            return
    
    print("\n[SUCCESS] Measurements table migration completed successfully!")

if __name__ == "__main__":
    migrate_measurements()

