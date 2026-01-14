"""
Migration script to add approval_status column to measurements table
Run this to add the approval_status field for measurement captain workflow
"""
from sqlalchemy import text
from app.db.database import engine, SessionLocal

def migrate_database():
    """Add approval_status column to measurements table"""
    print("Starting database migration: Adding approval_status to measurements...")
    
    with engine.connect() as conn:
        # Check if approval_status column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='measurements' AND column_name='approval_status'
        """))
        
        if result.fetchone() is None:
            print("Adding 'approval_status' column to measurements table...")
            # Add column with default value 'approved' for existing records
            conn.execute(text("""
                ALTER TABLE measurements 
                ADD COLUMN approval_status VARCHAR NOT NULL DEFAULT 'approved'
            """))
            # Create index for better query performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_measurements_approval_status 
                ON measurements(approval_status)
            """))
            conn.commit()
            print("[OK] Added 'approval_status' column and index")
        else:
            print("[OK] 'approval_status' column already exists")
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate_database()

