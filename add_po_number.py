#!/usr/bin/env python3
"""
Script to add po_number column to production_papers table
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def add_po_number_column():
    """Add po_number column to production_papers table"""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'admin')
        )
        
        cursor = conn.cursor()
        
        # Add the column
        print("Adding po_number column to production_papers table...")
        cursor.execute("ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS po_number VARCHAR;")
        
        # Verify it was added
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'production_papers' AND column_name = 'po_number'
        """)
        result = cursor.fetchone()
        
        conn.commit()
        
        if result:
            print(f"SUCCESS: Column po_number added: {result}")
            return True
        else:
            print("INFO: Column po_number already existed")
            return True
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = add_po_number_column()
    if success:
        print("Operation completed successfully!")
    else:
        print("Operation failed!")
