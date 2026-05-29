"""
Database initialization — creates all tables.
"""

from rich.console import Console

from src.database.db import get_engine
from src.database.models import Base

console = Console()


def init_database(database_url: str | None = None) -> None:
    """Create all database tables, dropping existing ones first.

    Args:
        database_url: Optional database URL override.
    """
    engine = get_engine(database_url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    console.print("[green][OK][/green] Database initialized successfully (all tables dropped and recreated).")
    console.print(f"  Tables created: {', '.join(Base.metadata.tables.keys())}")


if __name__ == "__main__":
    init_database()
