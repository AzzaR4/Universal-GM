"""AI provider configuration CRUD + connection testing."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider_registry import build_provider
from app.api.deps import db_session
from app.api.schemas import ProviderCreate, ProviderOut, ProviderUpdate
from app.core.security import encrypt_secret
from app.db.models import AIProvider

router = APIRouter(prefix="/api/settings/providers", tags=["settings"])


def _to_out(model: AIProvider) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "provider_type": model.provider_type,
        "endpoint_url": model.endpoint_url,
        "model_name": model.model_name,
        "has_api_key": bool(model.api_key_encrypted),
        "temperature": model.temperature,
        "max_tokens": model.max_tokens,
        "context_window": model.context_window,
        "extra_params": model.extra_params or {},
        "is_active": model.is_active,
    }


async def _deactivate_all(session: AsyncSession) -> None:
    await session.execute(update(AIProvider).values(is_active=False))


@router.get("/presets")
async def provider_presets() -> list[dict]:
    """UI presets for common OpenAI-compatible providers."""
    return [
        {"name": "OpenAI", "endpoint_url": "https://api.openai.com/v1", "model_name": "gpt-4o-mini", "requires_key": True},
        {"name": "Ollama (local)", "endpoint_url": "http://localhost:11434/v1", "model_name": "llama3.1", "requires_key": False},
        {"name": "LM Studio (local)", "endpoint_url": "http://localhost:1234/v1", "model_name": "local-model", "requires_key": False},
        {"name": "Groq", "endpoint_url": "https://api.groq.com/openai/v1", "model_name": "llama-3.3-70b-versatile", "requires_key": True},
        {"name": "Custom", "endpoint_url": "", "model_name": "", "requires_key": False},
    ]


@router.get("", response_model=list[ProviderOut])
async def list_providers(session: AsyncSession = Depends(db_session)) -> list[dict]:
    rows = (await session.execute(select(AIProvider))).scalars().all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=ProviderOut)
async def create_provider(
    payload: ProviderCreate, session: AsyncSession = Depends(db_session)
) -> dict:
    if payload.is_active:
        await _deactivate_all(session)
    model = AIProvider(
        name=payload.name,
        provider_type=payload.provider_type,
        endpoint_url=payload.endpoint_url,
        model_name=payload.model_name,
        api_key_encrypted=encrypt_secret(payload.api_key),
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        context_window=payload.context_window,
        extra_params=payload.extra_params,
        is_active=payload.is_active,
    )
    session.add(model)
    await session.commit()
    await session.refresh(model)
    return _to_out(model)


@router.patch("/{provider_id}", response_model=ProviderOut)
async def update_provider(
    provider_id: str,
    payload: ProviderUpdate,
    session: AsyncSession = Depends(db_session),
) -> dict:
    model = await session.get(AIProvider, provider_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_active"):
        await _deactivate_all(session)
    if "api_key" in data:
        api_key = data.pop("api_key")
        if api_key:  # only overwrite when a new key is supplied
            model.api_key_encrypted = encrypt_secret(api_key)
    for field, value in data.items():
        setattr(model, field, value)
    await session.commit()
    await session.refresh(model)
    return _to_out(model)


@router.post("/{provider_id}/activate", response_model=ProviderOut)
async def activate_provider(
    provider_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    model = await session.get(AIProvider, provider_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    await _deactivate_all(session)
    model.is_active = True
    await session.commit()
    await session.refresh(model)
    return _to_out(model)


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    model = await session.get(AIProvider, provider_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    await session.delete(model)
    await session.commit()
    return {"deleted": provider_id}


@router.post("/{provider_id}/test")
async def test_provider(
    provider_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    model = await session.get(AIProvider, provider_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    provider = build_provider(model)
    result = await provider.test_connection()
    return {
        "ok": result.ok,
        "latency_ms": result.latency_ms,
        "detail": result.detail,
        "model": result.model,
    }
