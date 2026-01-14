"""
Migration script to unify MeasurementEntry into Measurement table
Run this to migrate data from measurement_entries to measurements table
"""
from sqlalchemy import text
from app.db.database import engine, SessionLocal
import json

def migrate_measurements():
    """Migrate MeasurementEntry data to Measurement table"""
    print("Starting measurement unification migration...")
    
    db = SessionLocal()
    try:
        with engine.connect() as conn:
            # Check if new columns exist, if not add them
            print("Checking for new columns...")
            
            # Check and add external_foam_patti
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='measurements' AND column_name='external_foam_patti'
            """))
            if result.fetchone() is None:
                print("Adding external_foam_patti column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN external_foam_patti VARCHAR"))
                conn.commit()
                print("[OK] Added external_foam_patti column")
            
            # Check and add measurement_time
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='measurements' AND column_name='measurement_time'
            """))
            if result.fetchone() is None:
                print("Adding measurement_time column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN measurement_time VARCHAR"))
                conn.commit()
                print("[OK] Added measurement_time column")
            
            # Check and add task_id
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='measurements' AND column_name='task_id'
            """))
            if result.fetchone() is None:
                print("Adding task_id column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN task_id INTEGER REFERENCES measurement_tasks(id)"))
                conn.commit()
                print("[OK] Added task_id column")
            
            # Check and add status
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='measurements' AND column_name='status'
            """))
            if result.fetchone() is None:
                print("Adding status column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN status VARCHAR DEFAULT 'draft'"))
                conn.commit()
                print("[OK] Added status column")
            
            # Check and add metadata
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='measurements' AND column_name='metadata'
            """))
            if result.fetchone() is None:
                print("Adding metadata column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN metadata TEXT"))
                conn.commit()
                print("[OK] Added metadata column")
            
            # Check and add rejection_reason
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='measurements' AND column_name='rejection_reason'
            """))
            if result.fetchone() is None:
                print("Adding rejection_reason column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN rejection_reason TEXT"))
                conn.commit()
                print("[OK] Added rejection_reason column")
            
            # Check and add approved_by
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='measurements' AND column_name='approved_by'
            """))
            if result.fetchone() is None:
                print("Adding approved_by column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN approved_by INTEGER REFERENCES users(id)"))
                conn.commit()
                print("[OK] Added approved_by column")
            
            # Check and add approved_at
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='measurements' AND column_name='approved_at'
            """))
            if result.fetchone() is None:
                print("Adding approved_at column...")
                conn.execute(text("ALTER TABLE measurements ADD COLUMN approved_at TIMESTAMP WITH TIME ZONE"))
                conn.commit()
                print("[OK] Added approved_at column")
            
            # Check if measurement_entries table exists
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name='measurement_entries'
            """))
            
            if result.fetchone():
                print("\nMigrating data from measurement_entries to measurements...")
                
                # Map category to measurement_type
                category_map = {
                    'Sample Frame': 'frame_sample',
                    'Sample Shutter': 'shutter_sample',
                    'Regular Frame': 'regular_frame',
                    'Regular Shutter': 'regular_shutter'
                }
                
                # Get all measurement_entries
                entries = conn.execute(text("""
                    SELECT * FROM measurement_entries
                    ORDER BY id
                """))
                
                migrated_count = 0
                skipped_count = 0
                
                for entry in entries:
                    entry_dict = dict(entry._mapping)
                    
                    # Check if measurement_number already exists in measurements
                    check_result = conn.execute(text("""
                        SELECT id FROM measurements 
                        WHERE measurement_number = :measurement_number
                    """), {"measurement_number": entry_dict['measurement_number']})
                    
                    if check_result.fetchone():
                        print(f"  [SKIP] Measurement {entry_dict['measurement_number']} already exists in measurements table")
                        skipped_count += 1
                        continue
                    
                    # Map category to measurement_type
                    measurement_type = category_map.get(entry_dict.get('category'), 'regular_shutter')
                    
                    # Prepare metadata
                    metadata = {}
                    if entry_dict.get('category'):
                        metadata['category'] = entry_dict['category']
                    if entry_dict.get('sent_to_production_at'):
                        metadata['sent_to_production_at'] = str(entry_dict['sent_to_production_at'])
                    if entry_dict.get('production_measurement_id'):
                        metadata['production_measurement_id'] = entry_dict['production_measurement_id']
                    
                    metadata_json = json.dumps(metadata) if metadata else None
                    
                    # Insert into measurements table
                    conn.execute(text("""
                        INSERT INTO measurements (
                            measurement_type, measurement_number, party_name, thickness,
                            measurement_date, site_location, items, notes,
                            approval_status, external_foam_patti, measurement_time,
                            task_id, status, metadata, created_by, created_at, updated_at
                        ) VALUES (
                            :measurement_type, :measurement_number, :party_name, :thickness,
                            :measurement_date, NULL, :items, :notes,
                            'pending_approval', :external_foam_patti, :measurement_time,
                            :task_id, :status, :metadata, :created_by, :created_at, :updated_at
                        )
                    """), {
                        "measurement_type": measurement_type,
                        "measurement_number": entry_dict['measurement_number'],
                        "party_name": entry_dict.get('party_name', ''),
                        "thickness": entry_dict.get('thickness'),
                        "measurement_date": entry_dict.get('measurement_date'),
                        "items": entry_dict.get('measurement_items', '[]'),
                        "notes": entry_dict.get('notes'),
                        "external_foam_patti": entry_dict.get('external_foam_patti'),
                        "measurement_time": entry_dict.get('measurement_time'),
                        "task_id": entry_dict.get('task_id'),
                        "status": entry_dict.get('status', 'draft'),
                        "metadata": metadata_json,
                        "created_by": entry_dict['created_by'],
                        "created_at": entry_dict.get('created_at'),
                        "updated_at": entry_dict.get('updated_at')
                    })
                    
                    migrated_count += 1
                    print(f"  [OK] Migrated measurement {entry_dict['measurement_number']}")
                
                conn.commit()
                print(f"\n[SUCCESS] Migration complete!")
                print(f"  - Migrated: {migrated_count} measurements")
                print(f"  - Skipped: {skipped_count} measurements (already exist)")
                print("\nNote: measurement_entries table is kept for reference but is now deprecated.")
            else:
                print("\n[INFO] measurement_entries table not found. No data to migrate.")
        
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_measurements()


