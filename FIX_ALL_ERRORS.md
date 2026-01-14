# Fix All Errors - Complete Guide

## Issues Fixed

### 1. **PD Number Removal** ✅
- **Frontend**: Removed all `pd_number` references from:
  - `CreateMeasurement.tsx` - Removed from form state and UI
  - `ViewMeasurement.tsx` - Removed from display
  - `Measurements.tsx` - Removed from table
  - `ViewParty.tsx` - Removed from measurements table
  - `ViewProductionPaper.tsx` - Removed from type definition
  - `measurement-captain/Measurements.tsx` - Removed from table

- **Backend**: Removed all `pd_number` references from:
  - `app/schemas/user.py` - Removed from `MeasurementBase` and `MeasurementEntryBase`
  - `app/db/models/user.py` - Removed from `Measurement` and `MeasurementEntry` models
  - `app/api/v1/endpoints/production.py` - Removed from API responses
  - `app/api/v1/endpoints/measurement_captain.py` - Removed from all endpoints

### 2. **Database Schema Issues** ⚠️

**Note**: The `pd_number` column may still exist in your database tables. This won't cause errors, but you can remove it for cleanliness.

**To check and fix database schema:**
```powershell
cd backend
python fix_all_db_issues.py
```

**Manual SQL to remove pd_number (PostgreSQL):**
```sql
ALTER TABLE measurements DROP COLUMN pd_number;
ALTER TABLE measurement_entries DROP COLUMN pd_number;
```

**Manual SQL to add site_location (if missing):**
```sql
ALTER TABLE measurements ADD COLUMN IF NOT EXISTS site_location VARCHAR;
```

### 3. **Uvicorn Command** ✅

**Correct command from backend directory:**
```powershell
cd backend
uvicorn app.main:app --reload
```

**Or from Projects directory:**
```powershell
uvicorn backend.app.main:app --reload
```

**Current issue**: You're running `uvicorn main:app --reload` which won't work because:
- `main.py` is at `backend/app/main.py`, not in the root
- The correct module path is `app.main:app`

### 4. **Code Fixes Applied** ✅

1. Fixed `db.refresh()` call - removed invalid parameter
2. Added proper `joinedload` import
3. Fixed measurement response to include `created_by_username`
4. Ensured all database models are properly imported in `init_db()`

## Steps to Run Server Correctly

1. **Navigate to backend directory:**
   ```powershell
   cd backend
   ```

2. **Activate virtual environment:**
   ```powershell
   venv\Scripts\Activate.ps1
   ```

3. **Check database schema (optional but recommended):**
   ```powershell
   python fix_all_db_issues.py
   ```

4. **Start the server:**
   ```powershell
   uvicorn app.main:app --reload
   ```

## Verification Checklist

- ✅ All `pd_number` references removed from code
- ✅ `site_location` field added to models and schemas
- ✅ Database models properly defined
- ✅ API endpoints fixed
- ✅ Frontend components updated
- ⚠️ Database columns may need manual cleanup (pd_number removal)

## If You Still Get Errors

1. **Import errors**: Make sure you're in the `backend` directory and virtual environment is activated
2. **Database errors**: Run `python fix_all_db_issues.py` to check schema
3. **Module not found**: Verify you're using the correct uvicorn command: `uvicorn app.main:app --reload`
