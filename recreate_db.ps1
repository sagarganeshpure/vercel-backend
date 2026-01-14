# Script to recreate database with new sales tables
Write-Host "Recreating database with new sales tables..." -ForegroundColor Yellow

# Backup existing database if it exists
if (Test-Path "app.db") {
    Write-Host "Backing up existing database..." -ForegroundColor Cyan
    Copy-Item "app.db" "app.db.backup" -ErrorAction SilentlyContinue
    Write-Host "Backup created: app.db.backup" -ForegroundColor Green
}

# Remove old database
if (Test-Path "app.db") {
    Remove-Item "app.db" -Force
    Write-Host "Old database removed." -ForegroundColor Green
}

# Initialize new database
Write-Host "Creating new database with all tables..." -ForegroundColor Cyan
python init_db.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Database recreated successfully!" -ForegroundColor Green
    Write-Host "You can now restart your backend server." -ForegroundColor Green
} else {
    Write-Host "Error creating database. Check the error messages above." -ForegroundColor Red
}

