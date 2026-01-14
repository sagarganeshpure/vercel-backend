# Fix Organization Slug Database Error - URGENT

## Problem
The database still has the `organization_slug` column with a NOT NULL constraint, but the code no longer provides this value. This causes registration errors:
```
null value in column "organization_slug" of relation "users" violates not-null constraint
```

## Quick Fix - Run SQL Directly

**Option 1: Using psql (Recommended)**
```powershell
# Connect to your database
psql -U your_username -d TestForProject

# Then run:
ALTER TABLE users ALTER COLUMN organization_slug DROP NOT NULL;
ALTER TABLE users DROP COLUMN organization_slug;
```

**Option 2: Using pgAdmin or any PostgreSQL client**
1. Connect to your database
2. Open Query Tool
3. Run these commands:
```sql
ALTER TABLE users ALTER COLUMN organization_slug DROP NOT NULL;
ALTER TABLE users DROP COLUMN organization_slug;
```

**Option 3: Using Python script (if psql not available)**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -c "from sqlalchemy import create_engine, text; from app.core.config import settings; engine = create_engine(settings.DATABASE_URL); conn = engine.connect(); conn.execute(text('ALTER TABLE users ALTER COLUMN organization_slug DROP NOT NULL')); conn.execute(text('ALTER TABLE users DROP COLUMN organization_slug')); conn.commit(); conn.close(); print('Fixed!')"
```

## Verification
After running the fix, verify the column is removed:
```sql
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'organization_slug';
```
Should return no rows.

## What Was Changed in Code
- ✅ Removed `organization_slug` from backend User model
- ✅ Removed `organization_slug` from backend schemas
- ✅ Removed `organization_slug` from backend API endpoints
- ✅ Removed `organization_slug` from frontend types
- ✅ Removed `organization_slug` from frontend components
- ⚠️ **Database column still needs to be removed** (run the SQL above)
