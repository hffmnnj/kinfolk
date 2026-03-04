"""
Database connection and session management.

SQLite with SQLAlchemy ORM.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # Required for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


def get_db():
    """Dependency: yield a database session, close on completion."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
