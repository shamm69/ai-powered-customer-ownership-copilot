"""SQLite database configuration for the application."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.runtime_configuration import get_database_path

DATABASE_PATH = get_database_path()
DATABASE_URL = f"sqlite+pysqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class shared by all SQLAlchemy ORM models."""


def get_db() -> Iterator[Session]:
    """Provide one database session for a request and close it afterward."""
    with SessionLocal() as session:
        yield session
