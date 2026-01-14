import os
from fastapi import FastAPI
from mangum import Mangum

# Read environment variables using os.getenv for production safety
DATABASE_URL = os.getenv("DATABASE_URL")

# Prefer importing the existing app if application logic lives in `app` package.
try:
    # If the project already defines a FastAPI instance at app.main.app, reuse it
    from app.main import app  # type: ignore
except Exception:
    # Fallback: create a minimal FastAPI app
    app = FastAPI()


@app.get("/")
def root():
    return {
        "message": "FastAPI running on Vercel 🚀",
        "database_url_present": bool(DATABASE_URL),
    }


# Mangum adapts FastAPI (ASGI) to serverless environments
handler = Mangum(app)
