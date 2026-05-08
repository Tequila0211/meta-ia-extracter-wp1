"""
Database engine and session management.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

# Default database path relative to project root
_DEFAULT_DB_URL = "sqlite:///data/project.sqlite"


def get_database_url() -> str:
    """Get the database URL from environment or default."""
    return os.getenv("DATABASE_URL", _DEFAULT_DB_URL)


def get_engine(database_url: str | None = None):
    """Create a SQLAlchemy engine.

    Args:
        database_url: Optional database URL override. Defaults to env/config value.
    """
    url = database_url or get_database_url()
    # For SQLite, ensure the directory exists
    if url.startswith("sqlite:///"):
        db_path = url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, echo=False)


def get_session(database_url: str | None = None) -> Session:
    """Create a new database session.

    Args:
        database_url: Optional database URL override.
    """
    engine = get_engine(database_url)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(self, database_url: str | None = None):
        self.engine = get_engine(database_url)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def get_session(self) -> Session:
        """Create a new session."""
        return self._session_factory()

    def __enter__(self):
        self.session = self.get_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
