"""
Migration script to create party_history table
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from app.core.config import settings
from app.db.base import Base
from sqlalchemy.orm import sessionmaker

# Create engine
engine = create_engine(str(settings.DATABASE_URL))

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def migrate():
    """Create party_history table"""
    db = SessionLocal()
    try:
        # Create the table
        from app.db.models.user import PartyHistory
        PartyHistory.__table__.create(bind=engine, checkfirst=True)
        print("Created party_history table successfully")
    except Exception as e:
        print(f"Error creating party_history table: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()

