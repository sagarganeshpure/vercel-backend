import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_po_number_column():
    """Check if po_number column exists in production_papers table"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'admin')
        )
        
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'production_papers' AND column_name = 'po_number'
        """)
        result = cursor.fetchone()
        
        if result:
            print(f"Column exists: {result}")
            return True
        else:
            print("Column does not exist")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def add_po_number_column():
    """Add po_number column to production_papers table"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'admin')
        )
        
        cursor = conn.cursor()
        
        # Add the column
        print("Adding po_number column...")
        cursor.execute("ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS po_number VARCHAR;")
        conn.commit()
        print("Column added successfully")
        return True
            
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # First check if column exists
    if not check_po_number_column():
        # Add it if it doesn't exist
        add_po_number_column()
        # Check again
        check_po_number_column()
    else:
        print("Column already exists")
