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
    add additive columns if they are missing. New tables are created by create_all.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(conn)

    # (table, column, DDL type) additive columns introduced across sessions.
    additive: list[tuple[str, str, str]] = [
        ("campaigns", "active_combat", "JSON"),
        ("campaigns", "current_session_id", "VARCHAR(36)"),
        ("characters", "player_name", "VARCHAR(200)"),
        ("memories", "tags", "JSON"),
        ("memories", "embedding", "JSON"),
        ("memories", "source_action_id", "VARCHAR(36)"),
        ("sessions", "key_events", "JSON"),
        ("sessions", "player_actions_count", "INTEGER DEFAULT 0"),
        ("sessions", "xp_awarded", "INTEGER"),
    ]
    for table, column, ddl_type in additive:
        try:
            columns = {c["name"] for c in inspector.get_columns(table)}
        except Exception:  # noqa: BLE001 - table may not exist yet on fresh DBs
            continue
        if column not in columns:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
