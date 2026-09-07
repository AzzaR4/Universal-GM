"""Pytest fixtures. Uses an isolated in-memory SQLite DB per test session."""
from __future__ import annotations

import os

# Ensure tests never touch the real DB or need a secret from the environment.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db import models  # noqa: F401


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def seeded_rng():
    """Deterministic RNG for dice tests."""
    import random

    return random.Random(1234)
