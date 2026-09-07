"""Loads the active AI provider from the database into a usable AIProvider."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_compatible import OpenAICompatibleProvider
from app.ai.provider_base import AIProvider, ProviderConfig
from app.core.exceptions import AIProviderError
from app.core.security import decrypt_secret
from app.db.models import AIProvider as AIProviderModel


def build_provider(model: AIProviderModel) -> AIProvider:
    config = ProviderConfig(
        endpoint_url=model.endpoint_url,
        model_name=model.model_name,
        api_key=decrypt_secret(model.api_key_encrypted),
        temperature=model.temperature,
        max_tokens=model.max_tokens,
        extra_params=model.extra_params or {},
    )
    # Only openai_compatible is implemented; all presets use it under the hood.
    return OpenAICompatibleProvider(config)


async def get_active_provider(session: AsyncSession) -> AIProvider:
    model = (
        await session.execute(
            select(AIProviderModel).where(AIProviderModel.is_active == True)  # noqa: E712
        )
    ).scalars().first()
    if model is None:
        raise AIProviderError(
            "No active AI provider configured. Open Settings to add and activate one."
        )
    return build_provider(model)


async def get_provider_by_id(session: AsyncSession, provider_id: str) -> AIProvider:
    model = await session.get(AIProviderModel, provider_id)
    if model is None:
        raise AIProviderError("AI provider not found.")
    return build_provider(model)
