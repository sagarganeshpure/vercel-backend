# Authentication Fix - Step by Step Guide

## Issues Found and Fixed

### 1. ✅ Missing Model Imports in `database.py`
**Problem:** The `init_db()` function was missing imports for:
- Dispatch models
- Logistics models
- Accounts models
- Some User models (ProductionSchedule, Product, etc.)

**Fix:** Updated `backend/app/db/database.py` to import ALL models

### 2. ✅ Database Tables Missing
**Problem:** New sales tables (leads, site_projects, quotations, sales_orders, etc.) don't exist in the database

**Fix:** Created database check and fix scripts

### 3. ✅ Role Pattern Updated
**Problem:** Sales roles (marketing_executive, sales_executive, sales_manager) were added to schema pattern

**Fix:** Already fixed in `backend/app/schemas/user.py`

## Step-by-Step Fix Instructions

### Step 1: Stop Backend Server
Press `Ctrl+C` in the terminal where your backend server is running.

### Step 2: Run Database Fix Script

Open PowerShell in the `backend` directory and run:

```powershell
cd C:\Users\sagar\OneDrive\Desktop\Projects\backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run the fix script
.\fix_database.ps1
```

**OR manually:**

```powershell
# Check database
python check_and_fix_db.py

# If issues found, recreate database
# Backup existing (optional)
if (Test-Path app.db) {
    Copy-Item app.db app.db.backup
}

# Remove old database
Remove-Item app.db -ErrorAction SilentlyContinue

# Create new database
python init_db.py
```

### Step 3: Verify Database

The script will:
- ✅ Check for duplicate tables
- ✅ Verify all required tables exist
- ✅ Recreate database if needed
- ✅ Backup existing database automatically

### Step 4: Restart Backend Server

```powershell
# Make sure you're in backend directory with venv activated
python -m uvicorn app.main:app --reload --port 8000
```

### Step 5: Test Authentication

1. Try logging in with existing credentials
2. If login fails, register a new user
3. The 500 error should be resolved

## Files Modified

1. ✅ `backend/app/db/database.py` - Added all missing model imports
2. ✅ `backend/app/main.py` - Added startup database check
3. ✅ `backend/app/schemas/user.py` - Sales roles added to pattern
4. ✅ `backend/check_and_fix_db.py` - Database verification script
5. ✅ `backend/fix_database.ps1` - Automated fix script

## Database Tables Created

The following tables will be created:
- ✅ users
- ✅ measurements
- ✅ parties
- ✅ production_papers
- ✅ leads (NEW)
- ✅ site_projects (NEW)
- ✅ quotations (NEW)
- ✅ sales_orders (NEW)
- ✅ measurement_requests (NEW)
- ✅ follow_ups (NEW)
- ✅ All other existing tables

## Troubleshooting

### If you still get 500 error:

1. **Check backend logs** - Look for specific error messages
2. **Verify database exists** - Check if `app.db` file exists in backend directory
3. **Check imports** - Make sure all Python packages are installed:
   ```powershell
   pip install -r requirements.txt
   ```
4. **Clear Python cache**:
   ```powershell
   Get-ChildItem -Path app -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
   ```

### If authentication still fails:

1. **Check user exists** - Try registering a new user
2. **Verify password hashing** - Check `backend/app/core/security.py`
3. **Check JWT tokens** - Verify SECRET_KEY in config

## Notes

- ⚠️ **Data Loss Warning:** Recreating the database will delete all existing data
- 💾 **Backup:** The script automatically backs up your database before recreating
- 🔄 **Restart Required:** Always restart the backend server after database changes
- 📝 **New Users:** After recreating database, you'll need to register users again

## Verification Checklist

- [ ] Database file exists (`app.db`)
- [ ] All tables created (check with `check_and_fix_db.py`)
- [ ] No duplicate tables
- [ ] Backend server starts without errors
- [ ] Login endpoint works (no 500 error)
- [ ] Registration works with sales roles
- [ ] JWT tokens are generated correctly

