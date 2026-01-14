"""
Migration script to add frame_requirements and door_requirements fields to parties table
Run this to add client requirements columns to existing parties table
"""
from sqlalchemy import text
from app.db.database import engine


def migrate_client_requirements_fields():
    """Add frame_requirements and door_requirements columns to parties table"""
    print("Starting client requirements fields migration...")
    
    with engine.connect() as conn:
        # Check if parties table exists
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='parties'
        """))
        
        if result.fetchone() is None:
            print("[ERROR] parties table does not exist. Please run migrate_db.py first.")
            return
        
        # List of new columns to add
        new_columns = [
            ("frame_requirements", "TEXT"),
            ("door_requirements", "TEXT"),
        ]
        
        # Add each column if it doesn't exist
        for column_name, column_type in new_columns:
            try:
                # Check if column exists
                result = conn.execute(text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='parties' AND column_name='{column_name}'
                """))
                
                if result.fetchone() is None:
                    # Column doesn't exist, add it
                    print(f"Adding column: {column_name}...")
                    conn.execute(text(f"ALTER TABLE parties ADD COLUMN {column_name} {column_type}"))
                    conn.commit()
                    print(f"[OK] Added column: {column_name}")
                else:
                    print(f"[SKIP] Column {column_name} already exists, skipping...")
                    
            except Exception as e:
                print(f"[ERROR] Failed to add column {column_name}: {str(e)}")
                conn.rollback()
        
        print("\n[SUCCESS] Client requirements fields migration completed!")


if __name__ == "__main__":
    migrate_client_requirements_fields()

