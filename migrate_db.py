"""
Migration script to add role column and new tables
Run this if you have an existing database
"""
from sqlalchemy import text
from app.db.database import engine, SessionLocal

def migrate_database():
    """Add missing columns and tables to existing database"""
    print("Starting database migration...")
    
    with engine.connect() as conn:
        # Check if role column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='role'
        """))
        
        if result.fetchone() is None:
            print("Adding 'role' column to users table...")
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user' NOT NULL"))
            conn.commit()
            print("[OK] Added 'role' column")
        else:
            print("[OK] 'role' column already exists")
        
        # Create measurements table
        print("Creating measurements table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS measurements (
                id SERIAL PRIMARY KEY,
                name VARCHAR NOT NULL,
                description TEXT,
                value VARCHAR NOT NULL,
                unit VARCHAR,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE
            )
        """))
        conn.commit()
        print("[OK] Created measurements table")
        
        # Create parties table
        print("Creating parties table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS parties (
                id SERIAL PRIMARY KEY,
                name VARCHAR NOT NULL UNIQUE,
                contact_person VARCHAR,
                email VARCHAR,
                phone VARCHAR,
                address TEXT,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE
            )
        """))
        conn.commit()
        print("[OK] Created parties table")
        
        # Create production_papers table
        print("Creating production_papers table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS production_papers (
                id SERIAL PRIMARY KEY,
                paper_number VARCHAR UNIQUE NOT NULL,
                title VARCHAR NOT NULL,
                description TEXT,
                party_id INTEGER REFERENCES parties(id),
                measurement_id INTEGER REFERENCES measurements(id),
                status VARCHAR DEFAULT 'draft' NOT NULL,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE
            )
        """))
        conn.commit()
        print("[OK] Created production_papers table")
        
        # Create indexes
        print("Creating indexes...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_measurements_created_by ON measurements(created_by)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parties_name ON parties(name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_parties_created_by ON parties(created_by)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_production_papers_number ON production_papers(paper_number)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_production_papers_created_by ON production_papers(created_by)"))
        conn.commit()
        print("[OK] Created indexes")
    
    print("\n[SUCCESS] Database migration completed successfully!")

if __name__ == "__main__":
    migrate_database()

