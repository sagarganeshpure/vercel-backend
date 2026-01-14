"""
Quick fix script to add the missing 'category' column to measurement_entries table.
Run this from the backend directory with your virtual environment activated.
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings

def fix_category_column():
    """Add category column to measurement_entries table"""
    try:
        # Create engine
        engine = create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
        )
        
        with engine.connect() as conn:
            # Check database type
            db_url = str(engine.url)
            
            if 'postgresql' in db_url or 'postgres' in db_url:
                # PostgreSQL
                # Check if column exists
                check_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'measurement_entries' AND column_name = 'category'
                """)
                result = conn.execute(check_query)
                if result.fetchone():
                    print("[OK] Column 'category' already exists in measurement_entries table")
                    return
                
                # Add the column
                alter_query = text("""
                    ALTER TABLE measurement_entries 
                    ADD COLUMN category VARCHAR
                """)
                conn.execute(alter_query)
                conn.commit()
                print("[OK] Successfully added 'category' column to measurement_entries table")
                
            elif 'sqlite' in db_url:
                # SQLite - check if column exists
                check_query = text("PRAGMA table_info(measurement_entries)")
                result = conn.execute(check_query)
                columns = [row[1] for row in result.fetchall()]
                
                if 'category' in columns:
                    print("[OK] Column 'category' already exists in measurement_entries table")
                    return
                
                print("[WARNING] SQLite detected. SQLite doesn't support ALTER TABLE ADD COLUMN easily.")
                print("   You may need to recreate the table or use a migration tool.")
                print("   For development, you can delete the database and run: python init_db.py")
                
            else:
                print(f"[WARNING] Unsupported database type: {db_url}")
                print("   Please manually add the column using your database management tool:")
                print("   ALTER TABLE measurement_entries ADD COLUMN category VARCHAR;")
                
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        print("\nManual fix:")
        print("Run this SQL command in your database:")
        print("ALTER TABLE measurement_entries ADD COLUMN category VARCHAR;")
        sys.exit(1)

if __name__ == "__main__":
    print("Fixing measurement_entries table...")
    db_url = settings.DATABASE_URL
    if '@' in db_url:
        db_display = db_url.split('@')[-1]
    else:
        db_display = db_url
    print(f"Database: {db_display}")
    fix_category_column()
    print("\n[SUCCESS] Done! You can now restart your backend server.")
