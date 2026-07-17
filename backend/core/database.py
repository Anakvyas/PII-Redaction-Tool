"""SQLAlchemy engine/session management. SQLite by default (zero-config, file-based);
point DATABASE_URL at Postgres in production without changing any code."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    # Table creation, not a migration tool: fine for SQLite/dev and for bootstrapping
    # a fresh Postgres instance. Swap for Alembic migrations once the schema stabilizes.
    import models  # noqa: F401 — ensures all model classes are registered on Base.metadata

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
