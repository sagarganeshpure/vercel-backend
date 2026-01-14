"""
Migration script to add new Party fields
Run this to update existing parties table with all new fields
"""
from sqlalchemy import text
from app.db.database import engine

def migrate_party_fields():
    """Add new columns to parties table"""
    print("Starting Party fields migration...")
    
    with engine.connect() as conn:
        # Check if parties table exists
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name='parties'
        """))
        
        if result.fetchone() is None:
            print("[ERROR] parties table does not exist. Please run migrate_db.py first.")
            return
        
        # List of new columns to add
        new_columns = [
            ("party_type", "VARCHAR NOT NULL DEFAULT 'Builder'"),
            ("display_name", "VARCHAR"),
            ("customer_code", "VARCHAR UNIQUE"),
            ("business_type", "VARCHAR"),
            ("contact_persons", "TEXT"),
            ("office_address_line1", "VARCHAR"),
            ("office_address_line2", "VARCHAR"),
            ("office_area", "VARCHAR"),
            ("office_city", "VARCHAR"),
            ("office_state", "VARCHAR"),
            ("office_pin_code", "VARCHAR"),
            ("office_country", "VARCHAR DEFAULT 'India'"),
            ("site_addresses", "TEXT"),
            ("gst_registration_type", "VARCHAR"),
            ("gstin_number", "VARCHAR"),
            ("pan_number", "VARCHAR"),
            ("state_code", "VARCHAR"),
            ("msme_udyam_number", "VARCHAR"),
            ("customer_category", "VARCHAR"),
            ("industry_type", "VARCHAR"),
            ("estimated_monthly_volume", "VARCHAR"),
            ("estimated_yearly_volume", "VARCHAR"),
            ("price_category", "VARCHAR"),
            ("assigned_sales_executive", "VARCHAR"),
            ("marketing_source", "VARCHAR"),
            ("payment_terms", "VARCHAR"),
            ("credit_limit", "VARCHAR"),
            ("credit_days", "INTEGER"),
            ("security_cheque_pdc", "BOOLEAN DEFAULT FALSE"),
            ("preferred_delivery_location", "VARCHAR"),
            ("unloading_responsibility", "VARCHAR"),
            ("working_hours_at_site", "VARCHAR"),
            ("special_instructions", "TEXT"),
            ("product_preferences", "TEXT"),
            ("documents", "TEXT"),
            ("customer_status", "VARCHAR DEFAULT 'Prospect'"),
            ("approval_status", "VARCHAR DEFAULT 'Draft'"),
        ]
        
        # Add each column if it doesn't exist
        for column_name, column_def in new_columns:
            try:
                # Check if column exists
                result = conn.execute(text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='parties' AND column_name='{column_name}'
                """))
                
                if result.fetchone() is None:
                    print(f"Adding '{column_name}' column...")
                    # Handle NOT NULL columns differently
                    if 'NOT NULL' in column_def and 'DEFAULT' not in column_def:
                        # For party_type, we need to set a default for existing rows
                        if column_name == 'party_type':
                            conn.execute(text(f"ALTER TABLE parties ADD COLUMN {column_name} VARCHAR"))
                            conn.execute(text("UPDATE parties SET party_type = 'Builder' WHERE party_type IS NULL"))
                            conn.execute(text(f"ALTER TABLE parties ALTER COLUMN {column_name} SET NOT NULL"))
                        else:
                            conn.execute(text(f"ALTER TABLE parties ADD COLUMN {column_name} {column_def}"))
                    else:
                        conn.execute(text(f"ALTER TABLE parties ADD COLUMN {column_name} {column_def}"))
                    conn.commit()
                    print(f"[OK] Added '{column_name}' column")
                else:
                    print(f"[SKIP] '{column_name}' column already exists")
            except Exception as e:
                print(f"[ERROR] Failed to add '{column_name}': {e}")
                conn.rollback()
        
        # Create indexes for new indexed columns
        indexes = [
            ("idx_parties_customer_code", "parties(customer_code)"),
            ("idx_parties_gstin", "parties(gstin_number)"),
            ("idx_parties_pan", "parties(pan_number)"),
        ]
        
        for index_name, index_def in indexes:
            try:
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}"))
                conn.commit()
                print(f"[OK] Created index {index_name}")
            except Exception as e:
                print(f"[SKIP] Index {index_name} may already exist: {e}")
    
    print("\n[SUCCESS] Party fields migration completed successfully!")

if __name__ == "__main__":
    migrate_party_fields()
