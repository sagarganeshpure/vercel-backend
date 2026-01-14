from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI()

# Set up CORS

app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup if needed"""
    # Auto-fix missing columns
    try:
        from app.auto_migrate import fix_missing_columns
        fix_missing_columns()
    except Exception as e:
        print(f"Auto-migrate failed: {e}")

    try:
        from app.db.database import init_db
        from sqlalchemy import inspect
        from app.db.database import engine
        
        # Check if users table exists
        try:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            if 'users' not in tables:
                print("Database tables not found. Initializing database...")
                init_db()
                print("Database initialized successfully!")
            else:
                print("Database tables already exist.")
        except Exception as db_error:
            print(f"Error checking database: {db_error}")
            print("Attempting to initialize database...")
            try:
                init_db()
                print("Database initialized successfully!")
            except Exception as init_error:
                print(f"Error initializing database: {init_error}")
                print("Please run 'python init_db.py' manually to create the database tables.")
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
        print("Please run 'python init_db.py' manually to create the database tables.")

@app.get("/")
async def root():
    return {"message": "Welcome to the API"}

@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests to avoid 404 errors"""
    from fastapi.responses import Response
    return Response(status_code=204)