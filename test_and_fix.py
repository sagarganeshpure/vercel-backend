import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    result_log = []
    
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
            result_log.append(f"Column already exists: {result}")
        else:
            result_log.append("Column does not exist, adding it...")
            cursor.execute("ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS po_number VARCHAR;")
            conn.commit()
            result_log.append("Column added successfully")
            
            # Verify it was added
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'production_papers' AND column_name = 'po_number'
            """)
            result = cursor.fetchone()
            if result:
                result_log.append(f"Verification successful: {result}")
            else:
                result_log.append("Verification failed")
        
        conn.close()
        
    except Exception as e:
        result_log.append(f"Error: {str(e)}")
    
    # Write results to file
    with open('db_fix_result.txt', 'w') as f:
        for line in result_log:
            f.write(line + '\n')
    
    print("Results written to db_fix_result.txt")

if __name__ == "__main__":
    main()
