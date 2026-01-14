
import sqlalchemy
from sqlalchemy import create_engine, text, inspect

# Hardcoded from .env
DATABASE_URL = "postgresql+psycopg2://postgres:Root@localhost:5432/TestForProject"

def fix_database():
    print(f"Connecting to {DATABASE_URL}...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            print("Connected successfully.")
            
            # Check columns
            inspector = inspect(engine)
            columns = {col['name'] for col in inspector.get_columns('production_papers')}
            print(f"Existing columns: {columns}")
            
            columns_to_add = [
                'total_quantity', 'wall_type', 'rebate', 'sub_frame', 
                'construction', 'cover_moulding', 'frontside_laminate', 
                'backside_laminate', 'grade', 'side_frame', 'filler', 
                'foam_bottom', 'frp_coating'
            ]
            
            for col in columns_to_add:
                if col not in columns:
                    print(f"Adding column {col}...")
                    try:
                        conn.execute(text(f"ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS {col} VARCHAR"))
                        print(f"  - Added {col}")
                    except Exception as e:
                        print(f"  - Failed to add {col}: {e}")
                else:
                    print(f"Column {col} already exists.")
            
            conn.commit()
            print("Migration completed.")
            
    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    fix_database()
