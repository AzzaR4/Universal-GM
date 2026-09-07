"""SQLAlchemy async engine, session factory, and declarative base."""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_dir(url: str) -> None:
    # For sqlite file URLs, make sure the parent directory exists.
    marker = "sqlite+aiosqlite:///"
    if url.startswith(marker):
        path = url[len(marker):]
        if path and path != ":memory:":
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables. Import models so they register with Base.metadata."""
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_lightweight_migrations)


def _lightweight_migrations(conn) -> None:
    """Add newly-introduced columns to existing tables (SQLite-friendly).

    create_all never ALTERs existing tables, so for a pre-existing dev database we
    add the additive `campaigns.active_combat` column if it is missing.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(conn)
    try:
        columns = {c["name"] for c in inspector.get_columns("campaigns")}
    except Exception:  # noqa: BLE001 - table may not exist yet on fresh DBs
        return
    if "active_combat" not in columns:
        conn.execute(text("ALTER TABLE campaigns ADD COLUMN active_combat JSON"))
