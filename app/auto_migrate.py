
from sqlalchemy import text, inspect
from app.db.database import engine

def fix_missing_columns():
    print("Checking for missing columns in production_papers...")
    try:
        inspector = inspect(engine)
        if 'production_papers' not in inspector.get_table_names():
            return
            
        columns = {col['name'] for col in inspector.get_columns('production_papers')}
        
        required_columns = [
            "total_quantity", "wall_type", "rebate", "sub_frame", 
            "construction", "cover_moulding", "frontside_laminate", 
            "backside_laminate", "grade", "side_frame", "filler", 
            "foam_bottom", "frp_coating", "frontside_design", "backside_design", "core"
        ]
        
        with engine.connect() as conn:
            for col in required_columns:
                if col not in columns:
                    print(f"Adding missing column: {col}")
                    try:
                        conn.execute(text(f"ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS {col} VARCHAR"))
                        print(f"  - Added {col}")
                    except Exception as e:
                        print(f"  - Failed to add {col}: {e}")
            conn.commit()
            print("Database schema check completed.")
            
    except Exception as e:
        print(f"Error checking/fixing database schema: {e}")
