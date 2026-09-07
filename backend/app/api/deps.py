"""Shared FastAPI dependencies."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_session


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session
