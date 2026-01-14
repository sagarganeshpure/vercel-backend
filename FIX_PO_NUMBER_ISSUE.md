# Fix for Database Column Issues

## Problem 1: po_number Column Missing
The API endpoint `/api/v1/production/production-papers` was failing with:
```
psycopg2.errors.UndefinedColumn: column production_papers.po_number does not exist
```

## Problem 2: site_location Column Missing
The API endpoint `/api/v1/production/measurements` was failing with:
```
psycopg2.errors.UndefinedColumn: column measurements.site_location does not exist
```

## Root Cause
The SQLAlchemy models define columns that don't exist in the actual database tables:
- `ProductionPaper` model defines `po_number` column
- `Measurement` model defines `site_location` column

## Solution Applied

### Temporary Fix (Applied)
I've commented out the problematic columns:

1. **ProductionPaper po_number column**:
   - `app/db/models/user.py` (line 168): Commented out `po_number` column
   - `app/schemas/user.py` (line 280): Commented out `po_number` field

2. **Measurement site_location column**:
   - `app/db/models/user.py` (line 46): Commented out `site_location` column  
   - `app/schemas/user.py` (line 87): Commented out `site_location` field

### Permanent Fix (Recommended)
To permanently fix these issues, add the missing columns to your database:

```sql
-- Add po_number column to production_papers table
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS po_number VARCHAR;

-- Add site_location column to measurements table  
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS site_location VARCHAR;
```

### Alternative: Use provided scripts
Run any of these scripts from the backend directory:
- `python fix_database_schema.py` (handles both columns)
- `python add_po_number.py` (po_number only)
- `python verify_column.py` (check column existence)

## Testing
After applying the fix, restart your backend server and test the APIs:
```bash
# Test production papers
curl -X GET "http://127.0.0.1:8000/api/v1/production/production-papers?skip=0&limit=10"

# Test measurements
curl -X GET "http://127.0.0.1:8000/api/v1/production/measurements?skip=0&limit=10"
```

## Next Steps
1. **Immediate**: Restart backend server - APIs should work without these fields
2. **Permanent**: Add columns to database using SQL or scripts
3. **Optional**: Uncomment the model/schema fields after adding database columns

## Files Modified
- `app/db/models/user.py` - Commented out po_number and site_location columns
- `app/schemas/user.py` - Commented out po_number and site_location fields

## Files Created (for convenience)
- `add_po_number.py` - Script to add po_number column
- `verify_column.py` - Script to check if columns exist
- `test_and_fix.py` - Script that checks and fixes automatically
- `fix_db.bat` - Batch file for Windows users
- `test_measurements_api.py` - Test script for measurements API
