# Fix Database Migration Error

## Problem
The error `column users.role does not exist` means your database doesn't have the new `role` column and tables we added.

## Solution

### Option 1: If using PostgreSQL (based on error)

Run the migration script:

```powershell
cd backend
python migrate_db.py
```

### Option 2: If using SQLite

Run the SQLite migration script:

```powershell
cd backend
python migrate_db_sqlite.py
```

### Option 3: Recreate Database (Simplest - if you don't have important data)

**For SQLite:**
```powershell
cd backend
del app.db
python init_db.py
```

**For PostgreSQL:**
You'll need to manually drop and recreate the database, or use the migration script above.

## After Migration

1. Restart your backend server
2. Try registering again
3. The error should be fixed

## Verify Migration

After running the migration, you can verify by checking:
- Users table has `role` column
- `measurements` table exists
- `parties` table exists
- `production_papers` table exists

