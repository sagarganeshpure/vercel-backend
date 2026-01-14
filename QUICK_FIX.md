# Quick Fix for "uvicorn not recognized"

## Immediate Solution

Since your virtual environment is already activated (you see `(venv)` in your prompt), run:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

## Or Install Uvicorn Directly

```powershell
python -m pip install uvicorn[standard]
python -m uvicorn app.main:app --reload --port 8000
```

## Why This Happened

The `uvicorn` command wasn't found because:
- Dependencies might not have been installed in the virtual environment
- PowerShell might not be finding the uvicorn executable

Using `python -m uvicorn` ensures we use the version from the virtual environment.

## After This Works

The updated `start.ps1` script now uses `python -m uvicorn` automatically, so this won't happen again.

