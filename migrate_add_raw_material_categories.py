"""
Migration script to add raw material categories table and category_id columns.

Run this to add raw material category management to the system.
Works with both PostgreSQL and SQLite.
"""
from sqlalchemy import text, inspect
from app.db.database import engine

def migrate_add_raw_material_categories():
    """Add raw material categories table and category_id columns"""
    print("Starting raw material categories migration...")
    
    # Check if using PostgreSQL or SQLite
    is_postgres = 'postgresql' in str(engine.url).lower() or 'postgres' in str(engine.url).lower()
    
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        # Create raw_material_categories table if it doesn't exist
        if 'raw_material_categories' not in inspector.get_table_names():
            print("Creating raw_material_categories table...")
            if is_postgres:
                conn.execute(text("""
                    CREATE TABLE raw_material_categories (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR NOT NULL UNIQUE,
                        code VARCHAR UNIQUE,
                        description TEXT,
                        is_active BOOLEAN NOT NULL DEFAULT TRUE,
                        created_by INTEGER NOT NULL REFERENCES users(id),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE raw_material_categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR NOT NULL UNIQUE,
                        code VARCHAR UNIQUE,
                        description TEXT,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        created_by INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users(id)
                    )
                """))
            conn.commit()
            print("[OK] Created raw_material_categories table")
        else:
            print("[SKIP] raw_material_categories table already exists")
        
        # Add category_id to raw_material_checks table
        if 'raw_material_checks' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('raw_material_checks')]
            if 'category_id' not in columns:
                print("Adding category_id column to raw_material_checks table...")
                if is_postgres:
                    conn.execute(text("""
                        ALTER TABLE raw_material_checks 
                        ADD COLUMN category_id INTEGER REFERENCES raw_material_categories(id)
                    """))
                else:
                    conn.execute(text("""
                        ALTER TABLE raw_material_checks 
                        ADD COLUMN category_id INTEGER
                    """))
                conn.commit()
                print("[OK] Added category_id column to raw_material_checks")
            else:
                print("[SKIP] category_id column already exists in raw_material_checks")
        else:
            print("[WARN] raw_material_checks table does not exist, skipping category_id addition")
        
        # Add category_id to orders table
        if 'orders' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('orders')]
            if 'category_id' not in columns:
                print("Adding category_id column to orders table...")
                if is_postgres:
                    conn.execute(text("""
                        ALTER TABLE orders 
                        ADD COLUMN category_id INTEGER REFERENCES raw_material_categories(id)
                    """))
                else:
                    conn.execute(text("""
                        ALTER TABLE orders 
                        ADD COLUMN category_id INTEGER
                    """))
                conn.commit()
                print("[OK] Added category_id column to orders")
            else:
                print("[SKIP] category_id column already exists in orders")
        else:
            print("[WARN] orders table does not exist, skipping category_id addition")
        
        # Create indexes for better query performance
        if is_postgres:
            try:
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_raw_material_checks_category_id 
                    ON raw_material_checks(category_id)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_orders_category_id 
                    ON orders(category_id)
                """))
                conn.commit()
                print("[OK] Created indexes on category_id columns")
            except Exception as e:
                print(f"[INFO] Could not create indexes (may already exist): {e}")
        else:
            try:
                conn.execute(text("""
                    CREATE INDEX idx_raw_material_checks_category_id 
                    ON raw_material_checks(category_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_orders_category_id 
                    ON orders(category_id)
                """))
                conn.commit()
                print("[OK] Created indexes on category_id columns")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    print(f"[INFO] Could not create indexes: {e}")
                else:
                    print("[SKIP] Indexes already exist")
        
        print("\n[SUCCESS] Raw material categories migration completed!")

if __name__ == "__main__":
    migrate_add_raw_material_categories()








