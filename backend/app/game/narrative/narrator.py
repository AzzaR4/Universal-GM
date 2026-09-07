"""Calls the AI provider and streams the narration text chunk by chunk."""
from __future__ import annotations

from collections.abc import AsyncIterator

from app.ai.provider_base import AIProvider


class Narrator:
    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    async def narrate(self, system: str, user: str) -> AsyncIterator[str]:
        async for chunk in self.provider.stream_text(system, user):
            yield chunk
