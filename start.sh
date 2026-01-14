#!/bin/bash

echo "Starting Backend Server..."

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << EOF
DATABASE_URL=sqlite:///./app.db
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://127.0.0.1:3000","http://127.0.0.1:5173"]
SECRET_KEY=your-secret-key-change-this-in-production-to-a-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
EOF
fi

pip install -r requirements.txt

if [ ! -f "app.db" ]; then
    echo "Initializing database..."
    python init_db.py
fi

echo "Starting server on http://localhost:8000"
uvicorn app.main:app --reload --port 8000

