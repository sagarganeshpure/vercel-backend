"""
Migration script to add edit remark tracking fields to measurements table
"""
from sqlalchemy import text, inspect, Column, Integer, Text, DateTime, ForeignKey
from app.db.database import engine

def migrate_add_edit_remark_fields():
    print("Starting edit remark fields migration for measurements...")
    inspector = inspect(engine)
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()

    with engine.connect() as conn:
        if 'measurements' not in inspector.get_table_names():
            print("ERROR: measurements table does not exist. Please run init_db() first.")
            return

        columns = [col['name'] for col in inspector.get_columns('measurements')]

        new_columns = [
            ("last_edit_remark", "TEXT", None, None, None),
            ("last_edited_by", "INTEGER", "measurements_last_edited_by_fkey", "users", "id"),
            ("last_edited_at", "TIMESTAMP", None, None, None),
        ]

        for col_name, col_type, fk_name, fk_table, fk_col in new_columns:
            if col_name not in columns:
                print(f"Adding {col_name} column...")
                if is_postgres:
                    if col_type == "TIMESTAMP":
                        conn.execute(text(f"ALTER TABLE measurements ADD COLUMN {col_name} TIMESTAMP WITH TIME ZONE"))
                    else:
                        conn.execute(text(f"ALTER TABLE measurements ADD COLUMN {col_name} {col_type}"))
                else:
                    if col_type == "TIMESTAMP":
                        conn.execute(text(f"ALTER TABLE measurements ADD COLUMN {col_name} DATETIME"))
                    else:
                        conn.execute(text(f"ALTER TABLE measurements ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"[OK] Added {col_name} column")
            else:
                print(f"[SKIP] {col_name} column already exists")

        # Update columns list after adding new columns
        columns = [col['name'] for col in inspector.get_columns('measurements')]
        
        # Add foreign key constraint for PostgreSQL if not exists
        if is_postgres and "last_edited_by" in columns:
            try:
                # Check if FK constraint exists
                fk_exists_query = text(f"""
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'measurements_last_edited_by_fkey' AND conrelid = 'measurements'::regclass
                """)
                fk_exists = conn.execute(fk_exists_query).fetchone()
                
                if not fk_exists:
                    print(f"Adding foreign key constraint for last_edited_by...")
                    conn.execute(text(f"ALTER TABLE measurements ADD CONSTRAINT measurements_last_edited_by_fkey FOREIGN KEY (last_edited_by) REFERENCES users(id)"))
                    conn.commit()
                    print("[OK] Added foreign key constraint")
                else:
                    print("[SKIP] Foreign key constraint for last_edited_by already exists")
            except Exception as e:
                print(f"[ERROR] Failed to add foreign key constraint: {e}")
                conn.rollback()

        # Add indexes for performance
        for col_name in ["last_edited_by", "last_edited_at"]:
            if col_name in columns:
                index_name = f"ix_measurements_{col_name}"
                try:
                    # Check if index exists
                    if is_postgres:
                        index_exists_query = text(f"""
                            SELECT 1 FROM pg_indexes
                            WHERE tablename = 'measurements' AND indexname = '{index_name}'
                        """)
                    else:
                        index_exists_query = text(f"""
                            SELECT 1 FROM sqlite_master
                            WHERE type = 'index' AND name = '{index_name}' AND tbl_name = 'measurements'
                        """)
                    index_exists = conn.execute(index_exists_query).fetchone()
                    
                    if not index_exists:
                        print(f"Creating index on {col_name}...")
                        conn.execute(text(f"CREATE INDEX {index_name} ON measurements ({col_name})"))
                        conn.commit()
                        print(f"[OK] Created index on {col_name}")
                    else:
                        print(f"[SKIP] Index on {col_name} already exists")
                except Exception as e:
                    print(f"[ERROR] Failed to create index on {col_name}: {e}")
                    conn.rollback()
        
        print("\n[SUCCESS] Edit remark fields migration completed!")

if __name__ == "__main__":
    migrate_add_edit_remark_fields()

