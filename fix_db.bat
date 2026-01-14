@echo off
cd /d "c:\Users\sagar\OneDrive\Desktop\Projects\backend"
python -c "
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'postgres'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'admin')
    )
    cursor = conn.cursor()
    cursor.execute('ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS po_number VARCHAR;')
    conn.commit()
    cursor.execute('SELECT column_name FROM information_schema.columns WHERE table_name = %s AND column_name = %s', ('production_papers', 'po_number'))
    result = cursor.fetchone()
    print('SUCCESS: po_number column added' if result else 'FAILED: po_number column not found')
    conn.close()
except Exception as e:
    print('ERROR:', str(e))
"
pause
