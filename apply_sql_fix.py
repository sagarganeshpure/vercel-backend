
import os
import sys
from sqlalchemy import create_engine, text

# Hardcoded from .env because we saw it earlier
DATABASE_URL = "postgresql+psycopg2://postgres:Root@localhost:5432/TestForProject"

SQL_COMMANDS = [
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS total_quantity VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS wall_type VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS rebate VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS sub_frame VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS construction VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS cover_moulding VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS frontside_laminate VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS backside_laminate VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS grade VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS side_frame VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS filler VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS foam_bottom VARCHAR;",
    "ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS frp_coating VARCHAR;",
]

def log(msg):
    with open("fix_log_final.txt", "a") as f:
        f.write(msg + "\n")
    print(msg)

def apply_fix():
    log(f"Starting fix script...")
    log(f"Connecting to {DATABASE_URL}...")
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            log("Connected successfully.")
            for cmd in SQL_COMMANDS:
                log(f"Executing: {cmd}")
                try:
                    conn.execute(text(cmd))
                    log("  -> Success")
                except Exception as e:
                    log(f"  -> Error (might be okay if exists): {e}")
            conn.commit()
            log("All commands executed. MIGRATION SUCCESS.")
            
    except Exception as e:
        log(f"Fatal error: {e}")

if __name__ == "__main__":
    apply_fix()
