
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import inspect, create_engine
# Hardcoded DB URL just to be safe/fast
DATABASE_URL = "postgresql+psycopg2://postgres:Root@localhost:5432/TestForProject"

def check_columns():
    try:
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        columns = {col['name'] for col in inspector.get_columns('production_papers')}
        required = [
            'total_quantity', 'wall_type', 'rebate', 'sub_frame', 'construction', 'cover_moulding',
            'frontside_laminate', 'backside_laminate', 'grade', 'side_frame', 'filler', 'foam_bottom', 'frp_coating'
        ]
        missing = [col for col in required if col not in columns]
        
        with open('verification_result.txt', 'w') as f:
            if missing:
                f.write(f"MISSING: {missing}")
            else:
                f.write("SUCCESS: ALL COLUMNS PRESENT")
    except Exception as e:
        with open('verification_result.txt', 'w') as f:
            f.write(f"ERROR: {e}")

if __name__ == "__main__":
    check_columns()
