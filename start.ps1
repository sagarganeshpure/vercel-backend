Write-Host "Starting Backend Server..." -ForegroundColor Green

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Cyan
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://www.python.org/" -ForegroundColor Yellow
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment!" -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
$activateScript = Join-Path $ScriptDir "venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Virtual environment activation may have issues, continuing anyway..." -ForegroundColor Yellow
    }
} else {
    Write-Host "ERROR: Virtual environment activation script not found!" -ForegroundColor Red
    exit 1
}

# Verify we're using venv Python
$pythonPath = (Get-Command python).Source
Write-Host "Using Python from: $pythonPath" -ForegroundColor Cyan

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    @"
DATABASE_URL=sqlite:///./app.db
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]
SECRET_KEY=your-secret-key-change-this-in-production-to-a-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host ".env file created successfully!" -ForegroundColor Green
}

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to install dependencies!" -ForegroundColor Red
    Write-Host "Please check requirements.txt and try again." -ForegroundColor Yellow
    exit 1
}
Write-Host "Dependencies installed successfully!" -ForegroundColor Green

# Verify uvicorn is installed
Write-Host "Verifying uvicorn installation..." -ForegroundColor Cyan
$uvicornCheck = python -m pip show uvicorn 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: uvicorn is not installed!" -ForegroundColor Red
    Write-Host "Installing uvicorn directly..." -ForegroundColor Yellow
    python -m pip install uvicorn
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install uvicorn!" -ForegroundColor Red
        exit 1
    }
}

# Initialize database if it doesn't exist
if (-not (Test-Path "app.db")) {
    Write-Host "Initializing database..." -ForegroundColor Yellow
    python init_db.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "WARNING: Database initialization may have failed!" -ForegroundColor Yellow
    }
}

# Start the server
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Starting server on http://localhost:8000" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Green

# Use python -m uvicorn to ensure we're using the venv version
python -m uvicorn app.main:app --reload --port 8000

