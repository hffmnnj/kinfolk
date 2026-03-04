"""
Database connection and session management.

SQLCipher-backed SQLite with SQLAlchemy ORM.
"""

import importlib

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings
from app.utils.crypto import (
    derive_sqlcipher_key_from_settings,
    sqlcipher_hex_literal,
)


def _load_sqlcipher_driver():
    """Load SQLCipher DB-API driver using binding fallback order."""
    # NOTE: Binding fallback order is pysqlcipher3 -> sqlcipher3 ->
    # sqlcipher-APSW.
    candidates = [
        ("pysqlcipher3.dbapi2", "pysqlcipher3"),
        ("sqlcipher3.dbapi2", "sqlcipher3"),
        ("sqlcipher3", "sqlcipher3"),
        ("sqlcipher_apsw.dbapi2", "sqlcipher-APSW"),
        ("sqlcipher_apsw", "sqlcipher-APSW"),
    ]
    errors: list[str] = []

    for module_name, _binding_name in candidates:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "connect"):
                return module
        except ModuleNotFoundError as exc:
            errors.append(f"{module_name}: {exc}")

    error_details = "; ".join(errors)
    raise RuntimeError(
        "No SQLCipher binding found. Install one of: "
        "pysqlcipher3, sqlcipher3, or sqlcipher-APSW. "
        f"Details: {error_details}"
    )


def _connect_sqlcipher():
    """Create a SQLCipher DB connection and apply encryption key."""
    dbapi_module = _load_sqlcipher_driver()
    sqlite_path = settings.database_url.removeprefix("sqlite:///")
    connection = dbapi_module.connect(sqlite_path, check_same_thread=False)

    derived_key = derive_sqlcipher_key_from_settings()
    pragma_key = sqlcipher_hex_literal(derived_key)
    cursor = connection.cursor()
    cursor.execute(f'PRAGMA key = "{pragma_key}"')
    cursor.close()

    return connection


engine = create_engine(
    "sqlite://",
    creator=_connect_sqlcipher,
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
