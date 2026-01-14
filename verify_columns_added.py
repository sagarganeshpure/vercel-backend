
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import inspect, text
from app.db.database import engine

def check_columns():
    inspector = inspect(engine)
    columns = {col['name'] for col in inspector.get_columns('production_papers')}
    required = [
        'total_quantity', 'wall_type', 'rebate', 'sub_frame', 'construction', 'cover_moulding',
        'frontside_laminate', 'backside_laminate', 'grade', 'side_frame', 'filler', 'foam_bottom', 'frp_coating'
    ]
    missing = [col for col in required if col not in columns]
    
    if missing:
        print(f"MISSING COLUMNS: {missing}")
    else:
        print("ALL COLUMNS PRESENT")

if __name__ == "__main__":
    check_columns()
