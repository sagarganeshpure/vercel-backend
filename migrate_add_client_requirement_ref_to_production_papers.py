"""
Migration script to add client requirement reference fields to production_papers table.

Run this to add client requirement tracking columns to existing production_papers table.
This allows tracking which client requirement (frame or door) was used to create each production paper.

Works with both PostgreSQL and SQLite.
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate_add_client_requirement_ref():
    """Add client requirement reference fields to production_papers table"""
    print("Starting client requirement reference fields migration...")
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        # Check if production_papers table exists
        if 'production_papers' not in inspector.get_table_names():
            print("[ERROR] production_papers table does not exist. Please run migrate_db.py first.")
            return
        
        columns = [col['name'] for col in inspector.get_columns('production_papers')]
        
        # Add client_requirement_party_id if it doesn't exist
        if 'client_requirement_party_id' not in columns:
            print("Adding client_requirement_party_id column...")
            if is_postgres:
                conn.execute(text("""
                    ALTER TABLE production_papers 
                    ADD COLUMN client_requirement_party_id INTEGER
                """))
            else:
                conn.execute(text("""
                    ALTER TABLE production_papers 
                    ADD COLUMN client_requirement_party_id INTEGER
                """))
            conn.commit()
            print("[OK] Added client_requirement_party_id column")
        else:
            print("[SKIP] client_requirement_party_id column already exists")
        
        # Add client_requirement_type if it doesn't exist
        if 'client_requirement_type' not in columns:
            print("Adding client_requirement_type column...")
            if is_postgres:
                conn.execute(text("""
                    ALTER TABLE production_papers 
                    ADD COLUMN client_requirement_type VARCHAR
                """))
            else:
                conn.execute(text("""
                    ALTER TABLE production_papers 
                    ADD COLUMN client_requirement_type VARCHAR
                """))
            conn.commit()
            print("[OK] Added client_requirement_type column")
        else:
            print("[SKIP] client_requirement_type column already exists")
        
        # Add client_requirement_index if it doesn't exist
        if 'client_requirement_index' not in columns:
            print("Adding client_requirement_index column...")
            if is_postgres:
                conn.execute(text("""
                    ALTER TABLE production_papers 
                    ADD COLUMN client_requirement_index INTEGER
                """))
            else:
                conn.execute(text("""
                    ALTER TABLE production_papers 
                    ADD COLUMN client_requirement_index INTEGER
                """))
            conn.commit()
            print("[OK] Added client_requirement_index column")
        else:
            print("[SKIP] client_requirement_index column already exists")
        
        # Create index on client_requirement_party_id for better query performance
        if is_postgres:
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_production_papers_client_req_party_id 
                    ON production_papers(client_requirement_party_id)
                """))
                conn.commit()
                print("[OK] Created index on client_requirement_party_id")
            except Exception as e:
                print(f"[INFO] Could not create index (may already exist): {e}")
        else:
            # SQLite doesn't support IF NOT EXISTS for indexes in older versions
            try:
                conn.execute(text("""
                    CREATE INDEX idx_production_papers_client_req_party_id 
                    ON production_papers(client_requirement_party_id)
                """))
                conn.commit()
                print("[OK] Created index on client_requirement_party_id")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"[INFO] Could not create index: {e}")
                else:
                    print("[SKIP] Index already exists")
        
        print("\n[SUCCESS] Client requirement reference fields migration completed!")

if __name__ == "__main__":
    migrate_add_client_requirement_ref()

