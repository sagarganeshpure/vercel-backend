# PowerShell script to fix database column issues
# This script adds missing columns to the database

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Database Column Fix Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & "venv\Scripts\Activate.ps1"
    } else {
        Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
        Write-Host "Please run: python -m venv venv" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Running migration script..." -ForegroundColor Green
Write-Host ""

python migrate_add_missing_columns.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Migration completed successfully!" -ForegroundColor Green
    Write-Host "You can now restart your backend server." -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Migration failed!" -ForegroundColor Red
    Write-Host "Please check the errors above." -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}
