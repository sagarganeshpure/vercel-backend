# Fix for Installation Issues

## Problem
You're getting errors because:
1. `httptools` (part of `uvicorn[standard]`) fails to build on Python 3.14
2. Dependencies aren't installing properly

## Solution

### Step 1: Clean Install

In your PowerShell (you're already in the backend folder with venv activated):

```powershell
# Uninstall any partially installed packages
python -m pip uninstall -y uvicorn httptools

# Install dependencies without httptools
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 2: If That Doesn't Work, Install Core Packages First

```powershell
# Install core packages one by one
python -m pip install fastapi
python -m pip install uvicorn
python -m pip install sqlalchemy
python -m pip install pydantic
python -m pip install python-jose[cryptography]
python -m pip install passlib[bcrypt]
python -m pip install python-multipart
python -m pip install email-validator
python -m pip install python-dotenv
python -m pip install alembic
```

### Step 3: Start the Server

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

## What Changed

I've updated `requirements.txt` to use `uvicorn` instead of `uvicorn[standard]` to avoid the `httptools` dependency that's causing build issues on Python 3.14.

The server will work fine without `httptools` - it's an optional performance optimization, not required.

