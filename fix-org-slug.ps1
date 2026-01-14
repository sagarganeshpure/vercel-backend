# PowerShell script to fix organization_slug column in database
# This script activates the virtual environment and runs the fix

Write-Host "Fixing organization_slug column in users table..." -ForegroundColor Cyan
Write-Host "This will make the column nullable (if needed) and then remove it." -ForegroundColor Yellow

# Check if we're in the backend directory
if (-not (Test-Path "venv")) {
    Write-Host "Error: venv not found. Please run this script from the backend directory." -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1

# Run the fix script
Write-Host "Running database fix script..." -ForegroundColor Yellow
python fix_organization_slug_database.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Database fix completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Database fix failed. Please check the error messages above." -ForegroundColor Red
    exit 1
}





