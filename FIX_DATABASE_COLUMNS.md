# Fix Database Column Errors

## Errors Found

1. **`column measurements.site_location does not exist`**
   - The model expects this column but it's missing in the database

2. **`column production_papers.po_number does not exist`**
   - The model expects this column but it's missing in the database

## Solution

### Option 1: Run SQL Migration (PostgreSQL)

If you're using PostgreSQL, run this SQL:

```sql
-- Add site_location to measurements
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS site_location VARCHAR;

-- Add po_number to production_papers
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS po_number VARCHAR;
```

Or use the migration file:
```bash
psql -U your_username -d your_database -f backend/migrate_add_columns.sql
```

### Option 2: Run Python Migration Script

1. **Activate virtual environment:**
   ```powershell
   cd backend
   venv\Scripts\Activate.ps1
   ```

2. **Run migration script:**
   ```powershell
   python migrate_add_missing_columns.py
   ```

### Option 3: Manual SQL (Any Database)

**For PostgreSQL:**
```sql
ALTER TABLE measurements ADD COLUMN site_location VARCHAR;
ALTER TABLE production_papers ADD COLUMN po_number VARCHAR;
```

**For SQLite:**
```sql
ALTER TABLE measurements ADD COLUMN site_location TEXT;
ALTER TABLE production_papers ADD COLUMN po_number TEXT;
```

## Quick Fix

The fastest way is to run the SQL directly in your database:

1. **Connect to your database** (using psql, pgAdmin, or any SQL client)
2. **Run the SQL commands** from `migrate_add_columns.sql`
3. **Restart your backend server**

## Verify Fix

After running the migration, verify the columns exist:

```sql
-- Check measurements table
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'measurements' AND column_name = 'site_location';

-- Check production_papers table
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'production_papers' AND column_name = 'po_number';
```

Both queries should return 1 row each.

## After Migration

1. ✅ Restart your backend server
2. ✅ The errors should be gone
3. ✅ API endpoints should work correctly
