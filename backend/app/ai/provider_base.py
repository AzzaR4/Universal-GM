"""Abstract AI provider interface.

Game logic NEVER imports the openai SDK directly; it depends only on this ABC.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    endpoint_url: str
    model_name: str
    api_key: str | None
    temperature: float = 0.8
    max_tokens: int = 1024
    extra_params: dict | None = None


@dataclass
class ConnectionTestResult:
    ok: bool
    latency_ms: float | None = None
    detail: str = ""
    model: str = ""


class AIProvider(ABC):
    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @abstractmethod
    async def complete_json(self, system: str, user: str) -> dict:
        """Non-streaming JSON-mode completion (used for intent parsing)."""

    @abstractmethod
    def stream_text(self, system: str, user: str) -> AsyncIterator[str]:
        """Streaming text completion (used for narration). Yields text chunks."""

    @abstractmethod
    async def test_connection(self) -> ConnectionTestResult:
        """Perform a minimal call and report success/failure/latency."""
