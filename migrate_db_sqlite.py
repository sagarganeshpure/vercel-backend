"""
Migration script for SQLite to add role column and new tables
Run this if you have an existing SQLite database
"""
from sqlalchemy import text, inspect
from app.db.database import engine, SessionLocal

def migrate_database():
    """Add missing columns and tables to existing SQLite database"""
    print("Starting database migration...")
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    with engine.connect() as conn:
        # Check if role column exists in users table
        if 'users' in existing_tables:
            columns = [col['name'] for col in inspector.get_columns('users')]
            if 'role' not in columns:
                print("Adding 'role' column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user' NOT NULL"))
                conn.commit()
                print("[OK] Added 'role' column")
            else:
                print("[OK] 'role' column already exists")
        
        # Create measurements table
        if 'measurements' not in existing_tables:
            print("Creating measurements table...")
            conn.execute(text("""
                CREATE TABLE measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR NOT NULL,
                    description TEXT,
                    value VARCHAR NOT NULL,
                    unit VARCHAR,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """))
            conn.commit()
            print("[OK] Created measurements table")
        else:
            print("[OK] measurements table already exists")
        
        # Create parties table
        if 'parties' not in existing_tables:
            print("Creating parties table...")
            conn.execute(text("""
                CREATE TABLE parties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR NOT NULL UNIQUE,
                    contact_person VARCHAR,
                    email VARCHAR,
                    phone VARCHAR,
                    address TEXT,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """))
            conn.commit()
            print("[OK] Created parties table")
        else:
            print("[OK] parties table already exists")
        
        # Create production_papers table
        if 'production_papers' not in existing_tables:
            print("Creating production_papers table...")
            conn.execute(text("""
                CREATE TABLE production_papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_number VARCHAR UNIQUE NOT NULL,
                    title VARCHAR NOT NULL,
                    description TEXT,
                    party_id INTEGER,
                    measurement_id INTEGER,
                    status VARCHAR DEFAULT 'draft' NOT NULL,
                    created_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id),
                    FOREIGN KEY (party_id) REFERENCES parties(id),
                    FOREIGN KEY (measurement_id) REFERENCES measurements(id)
                )
            """))
            conn.commit()
            print("[OK] Created production_papers table")
        else:
            print("[OK] production_papers table already exists")
    
    print("\n[SUCCESS] Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()

