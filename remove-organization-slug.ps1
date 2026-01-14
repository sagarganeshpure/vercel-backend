# PowerShell script to remove organization_slug column from users table
# This script activates the virtual environment and runs the migration

Write-Host "Removing organization_slug column from users table..." -ForegroundColor Cyan

# Check if we're in the backend directory
if (-not (Test-Path "venv")) {
    Write-Host "Error: venv not found. Please run this script from the backend directory." -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Run the migration script
Write-Host "Running migration script..." -ForegroundColor Yellow
python migrate_remove_organization_slug.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Migration completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Migration failed. Please check the error messages above." -ForegroundColor Red
    exit 1
}
