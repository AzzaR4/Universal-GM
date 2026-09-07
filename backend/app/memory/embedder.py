"""Embedding provider abstraction for semantic memory.

Three implementations are provided:

- ``OpenAIEmbedder``  — calls an OpenAI-compatible ``/embeddings`` endpoint using
  the same provider config already stored for the campaign.
- ``LocalEmbedder``   — sentence-transformers (optional dependency). Only used if
  the package is installed; otherwise construction raises.
- ``NullEmbedder``    — returns ``[]`` so retrieval transparently falls back to
  keyword search. This keeps the app fully functional without any AI configured.
"""
from __future__ import annotations

import math
from typing import Protocol, runtime_checkable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider_base import ProviderConfig
from app.core.security import decrypt_secret
from app.db.models import AIProvider as AIProviderModel


@runtime_checkable
class EmbeddingProvider(Protocol):
    async def embed(self, text: str) -> list[float]:
        ...


class NullEmbedder:
    """No-op embedder. Signals callers to use keyword retrieval instead."""

    async def embed(self, text: str) -> list[float]:  # noqa: D401
        return []


class OpenAIEmbedder:
    """Embeds text via an OpenAI-compatible embeddings endpoint."""

    def __init__(
        self, config: ProviderConfig, model: str = "text-embedding-3-small"
    ) -> None:
        from openai import AsyncOpenAI

        self.model = model
        self._client = AsyncOpenAI(
            base_url=config.endpoint_url or "https://api.openai.com/v1",
            api_key=config.api_key or "not-needed",
        )

    async def embed(self, text: str) -> list[float]:
        try:
            resp = await self._client.embeddings.create(
                model=self.model, input=text or ""
            )
            return list(resp.data[0].embedding)
        except Exception:  # noqa: BLE001 - degrade to keyword fallback on any error
            return []


class LocalEmbedder:
    """sentence-transformers embedder (optional dependency)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer  # type: ignore

        self._model = SentenceTransformer(model_name)

    async def embed(self, text: str) -> list[float]:
        vec = self._model.encode(text or "")
        return [float(x) for x in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors (0.0 if degenerate)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


async def get_embedder(session: AsyncSession) -> EmbeddingProvider:
    """Return the best available embedder given the active provider config.

    Falls back to ``NullEmbedder`` when no active AI provider is configured, which
    keeps memory retrieval working via keyword search.
    """
    model = (
        await session.execute(
            select(AIProviderModel).where(AIProviderModel.is_active == True)  # noqa: E712
        )
    ).scalars().first()
    if model is None:
        return NullEmbedder()
    try:
        config = ProviderConfig(
            endpoint_url=model.endpoint_url,
            model_name=model.model_name,
            api_key=decrypt_secret(model.api_key_encrypted),
            temperature=model.temperature,
            max_tokens=model.max_tokens,
            extra_params=model.extra_params or {},
        )
        embed_model = (model.extra_params or {}).get(
            "embedding_model", "text-embedding-3-small"
        )
        return OpenAIEmbedder(config, model=embed_model)
    except Exception:  # noqa: BLE001
        return NullEmbedder()
