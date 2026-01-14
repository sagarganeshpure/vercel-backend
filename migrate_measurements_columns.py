"""
Migration script to add missing columns to measurements table
Run this if you have an existing database
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate_measurements_columns():
    """Add missing columns to measurements table"""
    print("Starting database migration for measurements table columns...")
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        if 'measurements' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('measurements')]
            
            # List of columns to add with their definitions
            columns_to_add = [
                ('external_foam_patti', 'VARCHAR', True),
                ('measurement_time', 'VARCHAR', True),
                ('task_id', 'INTEGER', True),
                ('status', 'VARCHAR DEFAULT \'draft\' NOT NULL', False),
                ('metadata_json', 'TEXT', True),
                ('rejection_reason', 'TEXT', True),
                ('approved_by', 'INTEGER', True),
                ('approved_at', 'TIMESTAMP WITH TIME ZONE' if is_postgres else 'TIMESTAMP', True),
            ]
            
            for col_name, col_type, nullable in columns_to_add:
                if col_name not in columns:
                    print(f"Adding '{col_name}' column to measurements table...")
                    null_clause = '' if not nullable else ''
                    if is_postgres:
                        if 'DEFAULT' in col_type:
                            conn.execute(text(f"ALTER TABLE measurements ADD COLUMN {col_name} {col_type}"))
                        else:
                            conn.execute(text(f"ALTER TABLE measurements ADD COLUMN {col_name} {col_type} {null_clause}"))
                    else:
                        if 'DEFAULT' in col_type:
                            conn.execute(text(f"ALTER TABLE measurements ADD COLUMN {col_name} {col_type}"))
                        else:
                            conn.execute(text(f"ALTER TABLE measurements ADD COLUMN {col_name} {col_type} {null_clause}"))
                    conn.commit()
                    print(f"[OK] Added '{col_name}' column")
                else:
                    print(f"[OK] '{col_name}' column already exists")
            
            # Add foreign key constraints if they don't exist
            if is_postgres:
                # Check if task_id foreign key exists
                try:
                    result = conn.execute(text("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_name='measurements' 
                        AND constraint_type='FOREIGN KEY'
                        AND constraint_name LIKE '%task_id%'
                    """))
                    if result.fetchone() is None and 'task_id' in columns:
                        print("Adding foreign key constraint for task_id...")
                        conn.execute(text("""
                            ALTER TABLE measurements 
                            ADD CONSTRAINT fk_measurements_task_id 
                            FOREIGN KEY (task_id) REFERENCES measurement_tasks(id)
                        """))
                        conn.commit()
                        print("[OK] Added foreign key constraint for task_id")
                except Exception as e:
                    print(f"[INFO] Foreign key constraint may already exist or table doesn't exist: {e}")
                
                # Check if approved_by foreign key exists
                try:
                    result = conn.execute(text("""
                        SELECT constraint_name 
                        FROM information_schema.table_constraints 
                        WHERE table_name='measurements' 
                        AND constraint_type='FOREIGN KEY'
                        AND constraint_name LIKE '%approved_by%'
                    """))
                    if result.fetchone() is None and 'approved_by' in columns:
                        print("Adding foreign key constraint for approved_by...")
                        conn.execute(text("""
                            ALTER TABLE measurements 
                            ADD CONSTRAINT fk_measurements_approved_by 
                            FOREIGN KEY (approved_by) REFERENCES users(id)
                        """))
                        conn.commit()
                        print("[OK] Added foreign key constraint for approved_by")
                except Exception as e:
                    print(f"[INFO] Foreign key constraint may already exist: {e}")
                
                # Create indexes if they don't exist
                indexes_to_create = [
                    ('ix_measurements_task_id', 'task_id'),
                    ('ix_measurements_status', 'status'),
                ]
                
                for index_name, column_name in indexes_to_create:
                    try:
                        if column_name in columns:
                            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON measurements({column_name})"))
                            conn.commit()
                            print(f"[OK] Created index {index_name}")
                    except Exception as e:
                        print(f"[INFO] Index {index_name} may already exist: {e}")
        else:
            print("[ERROR] 'measurements' table does not exist")
            return
    
    print("\n[SUCCESS] Measurements table columns migration completed successfully!")

if __name__ == "__main__":
    migrate_measurements_columns()

