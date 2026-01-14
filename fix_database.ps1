# Comprehensive Database Fix Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Database Fix and Verification Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "app.db") -and -not (Test-Path "init_db.py")) {
    Write-Host "❌ Error: Please run this script from the backend directory" -ForegroundColor Red
    exit 1
}

# Step 1: Check database
Write-Host "Step 1: Checking database..." -ForegroundColor Yellow
python check_and_fix_db.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Step 2: Database has issues. Recreating..." -ForegroundColor Yellow
    
    # Backup if exists
    if (Test-Path "app.db") {
        $backupName = "app.db.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
        Copy-Item "app.db" $backupName -ErrorAction SilentlyContinue
        Write-Host "✅ Backed up to: $backupName" -ForegroundColor Green
    }
    
    # Remove old database
    Remove-Item "app.db" -ErrorAction SilentlyContinue
    
    # Recreate
    Write-Host "🔄 Creating new database..." -ForegroundColor Cyan
    python init_db.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database recreated successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to create database. Check errors above." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Step 3: Verifying database structure..." -ForegroundColor Yellow
python check_and_fix_db.py

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Database fix complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Restart your backend server" -ForegroundColor White
Write-Host "2. Try logging in again" -ForegroundColor White
Write-Host "3. If you had existing data, it's backed up in app.db.backup.*" -ForegroundColor White

