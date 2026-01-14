Write-Host "=== Backend Diagnostic Test ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check Python
Write-Host "1. Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   ✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Python NOT found!" -ForegroundColor Red
    exit 1
}

# Test 2: Check if venv exists
Write-Host "2. Checking virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "   ✓ Virtual environment exists" -ForegroundColor Green
} else {
    Write-Host "   ⚠ Virtual environment does NOT exist (will be created)" -ForegroundColor Yellow
}

# Test 3: Check if .env exists
Write-Host "3. Checking .env file..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "   ✓ .env file exists" -ForegroundColor Green
} else {
    Write-Host "   ⚠ .env file does NOT exist (will be created)" -ForegroundColor Yellow
}

# Test 4: Check if requirements.txt exists
Write-Host "4. Checking requirements.txt..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    Write-Host "   ✓ requirements.txt exists" -ForegroundColor Green
} else {
    Write-Host "   ✗ requirements.txt NOT found!" -ForegroundColor Red
    exit 1
}

# Test 5: Check if app/main.py exists
Write-Host "5. Checking app structure..." -ForegroundColor Yellow
if (Test-Path "app\main.py") {
    Write-Host "   ✓ app/main.py exists" -ForegroundColor Green
} else {
    Write-Host "   ✗ app/main.py NOT found!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== All checks passed! ===" -ForegroundColor Green
Write-Host "You can now run: .\start.ps1" -ForegroundColor Cyan

