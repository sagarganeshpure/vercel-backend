# Backend Server

## Quick Start

### Windows (PowerShell)
```powershell
.\start.ps1
```

### Windows (Git Bash) / Mac / Linux
```bash
chmod +x start.sh
./start.sh
# Or simply: bash start.sh
```

### Manual Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Initialize database (if not already done)
python init_db.py

# Start the server
uvicorn app.main:app --reload --port 8000
```

The server will be running at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- API docs: `http://localhost:8000/docs`
- Alternative docs: `http://localhost:8000/redoc`

