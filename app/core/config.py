from datetime import timedelta
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import json
import secrets

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"]
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-here-change-this-in-production"
    REFRESH_SECRET_KEY: str = "your-refresh-secret-key-here-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

settings = Settings()

# Generate a unique server instance ID on startup
# This changes every time the server restarts, invalidating all existing tokens
SERVER_INSTANCE_ID: str = secrets.token_urlsafe(32)

