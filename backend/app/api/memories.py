"""Memory API: list (filterable), create (manual), delete."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.api.schemas import MemoryCreate, MemoryOut
from app.db.models import Campaign, Memory
from app.game.memory.memory_manager import extract_keywords
from app.memory.embedder import get_embedder

router = APIRouter(prefix="/api/campaigns/{campaign_id}/memories", tags=["memories"])


def _to_out(m: Memory) -> MemoryOut:
    return MemoryOut(
        id=m.id,
        campaign_id=m.campaign_id,
        memory_type=m.memory_type,
        subject_id=m.subject_id,
        content=m.content,
        importance=m.importance,
        keywords=m.keywords or [],
        tags=m.tags or [],
        has_embedding=bool(m.embedding),
        source_action_id=m.source_action_id,
        created_at=m.created_at,
    )


@router.get("", response_model=list[MemoryOut])
async def list_memories(
    campaign_id: str,
    tag: str | None = None,
    min_importance: float | None = None,
    q: str | None = None,
    session: AsyncSession = Depends(db_session),
) -> list[MemoryOut]:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    rows = (
        await session.execute(
            select(Memory)
            .where(Memory.campaign_id == campaign_id)
            .order_by(Memory.created_at.desc())
        )
    ).scalars().all()

    result = []
    for m in rows:
        if tag is not None and tag not in (m.tags or []):
            continue
        if min_importance is not None and (m.importance or 0) < min_importance:
            continue
        if q is not None and q.lower() not in (m.content or "").lower():
            continue
        result.append(_to_out(m))
    return result


@router.post("", response_model=MemoryOut)
async def create_memory(
    campaign_id: str,
    payload: MemoryCreate,
    session: AsyncSession = Depends(db_session),
) -> MemoryOut:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    embedder = await get_embedder(session)
    embedding = []
    try:
        embedding = await embedder.embed(payload.content)
    except Exception:  # noqa: BLE001
        embedding = []

    mem = Memory(
        campaign_id=campaign_id,
        memory_type=payload.memory_type,
        subject_id=payload.subject_id,
        content=payload.content,
        importance=payload.importance,
        keywords=extract_keywords(payload.content),
        tags=payload.tags,
        embedding=embedding or None,
    )
    session.add(mem)
    await session.commit()
    await session.refresh(mem)
    return _to_out(mem)


@router.delete("/{memory_id}")
async def delete_memory(
    campaign_id: str,
    memory_id: str,
    session: AsyncSession = Depends(db_session),
) -> dict:
    mem = await session.get(Memory, memory_id)
    if mem is None or mem.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    await session.delete(mem)
    await session.commit()
    return {"deleted": memory_id}
