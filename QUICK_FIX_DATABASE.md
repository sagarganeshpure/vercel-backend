# Quick Fix Database Column Errors

## The Problem

You're getting these errors:
- `column measurements.site_location does not exist`
- `column production_papers.po_number does not exist`

## Quick Solution

### Step 1: Run the Migration Script

**Option A: Use PowerShell script (Easiest)**
```powershell
cd backend
.\fix-db-columns.ps1
```

**Option B: Manual Python script**
```powershell
cd backend
venv\Scripts\Activate.ps1
python migrate_add_missing_columns.py
```

**Option C: Run SQL directly (PostgreSQL)**

Connect to your database and run:
```sql
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS site_location VARCHAR;
ALTER TABLE production_papers ADD COLUMN IF NOT EXISTS po_number VARCHAR;
```

### Step 2: Restart Backend Server

After running the migration:
```powershell
# Stop current server (Ctrl+C)
# Then restart:
uvicorn app.main:app --reload
```

## What the Script Does

1. ✅ Checks if `site_location` column exists in `measurements` table
2. ✅ Adds it if missing
3. ✅ Checks if `po_number` column exists in `production_papers` table
4. ✅ Adds it if missing

## Verify It Worked

After migration, you should see:
```
[OK] Added 'site_location' column
[OK] Added 'po_number' column
Migration completed successfully!
```

Then restart your server and the errors should be gone!
