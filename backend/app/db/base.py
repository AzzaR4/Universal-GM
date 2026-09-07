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
