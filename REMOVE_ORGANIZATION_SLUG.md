# Remove Organization Slug - Migration Guide

This guide explains how to remove the `organization_slug` column from the database, backend, and frontend.

## Overview

The `organization_slug` field has been completely removed from:
- Database schema (User model)
- Backend API schemas (UserBase, UserCreate)
- Backend API endpoints (auth.py, admin.py)
- Frontend types and components
- Frontend forms (AdminUserManagement)

## Database Migration

### Option 1: Using Python Script (Recommended for PostgreSQL)

1. Activate the backend virtual environment:
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   ```

2. Run the migration script:
   ```powershell
   python migrate_remove_organization_slug.py
   ```

### Option 2: Using SQL Script (PostgreSQL only)

1. Connect to your PostgreSQL database using psql or a database client.

2. Run the SQL script:
   ```sql
   \i migrate_remove_organization_slug.sql
   ```

   Or copy and paste the contents of `migrate_remove_organization_slug.sql` into your database client.

### Option 3: Manual SQL (PostgreSQL)

If you prefer to run the SQL manually:

```sql
ALTER TABLE users DROP COLUMN organization_slug;
```

**Note for SQLite users**: SQLite does not support `DROP COLUMN` directly. You would need to:
1. Create a new table without the `organization_slug` column
2. Copy data from the old table to the new table
3. Drop the old table and rename the new table

Consider using Alembic for SQLite migrations.

## What Was Changed

### Backend Changes

1. **`backend/app/db/models/user.py`**: Removed `organization_slug` column from User model
2. **`backend/app/schemas/user.py`**: Removed `organization_slug` from `UserBase` schema
3. **`backend/app/api/v1/endpoints/auth.py`**: Removed organization_slug generation logic from registration
4. **`backend/app/api/v1/endpoints/admin.py`**: Removed organization_slug from user creation

### Frontend Changes

1. **`frontend/src/context/AuthContext.tsx`**: Removed `organization_slug` from User type
2. **`frontend/src/components/Navbar.tsx`**: Removed organization_slug display
3. **`frontend/src/components/SupervisorNavbar.tsx`**: Removed organization_slug display
4. **`frontend/src/pages/admin/AdminUserManagement.tsx`**: Removed organization_slug input field from form

## Verification

After running the migration:

1. **Check Database**: Verify the column is removed:
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'users' AND column_name = 'organization_slug';
   ```
   Should return no rows.

2. **Test Backend**: Try creating a new user via the API - it should work without organization_slug.

3. **Test Frontend**: 
   - Check that the Admin User Management form no longer shows "Organization Slug" field
   - Check that Navbar and SupervisorNavbar no longer display organization_slug
   - Try creating a new user - it should work without organization_slug

## Rollback (if needed)

If you need to rollback this change:

1. Add the column back to the database:
   ```sql
   ALTER TABLE users ADD COLUMN organization_slug VARCHAR NOT NULL DEFAULT '';
   ```

2. Restore the code changes from git history:
   ```bash
   git checkout HEAD~1 -- backend/app/db/models/user.py
   git checkout HEAD~1 -- backend/app/schemas/user.py
   # ... etc
   ```

## Notes

- Existing users in the database will have their `organization_slug` column removed
- No data migration is needed as organization_slug is not critical data
- The frontend will automatically stop showing organization_slug once the code is updated
