"""
MeetSmart AI — SQLAlchemy database engine + session factory.
Uses SQLite via aiosqlite for async support.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from src.utils.config import settings

# Synchronous engine (SQLite)
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist (called at app startup)."""
    from src.db import models  # noqa: F401 — import triggers table registration
    Base.metadata.create_all(bind=engine)
