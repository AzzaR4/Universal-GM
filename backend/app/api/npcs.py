"""NPC CRUD within a campaign."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.api.schemas import NPCCreate, NPCOut, NPCUpdate
from app.db.models import NPC, Campaign

router = APIRouter(prefix="/api/campaigns/{campaign_id}/npcs", tags=["npcs"])


@router.post("", response_model=NPCOut)
async def create_npc(
    campaign_id: str, payload: NPCCreate, session: AsyncSession = Depends(db_session)
) -> NPC:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    npc = NPC(campaign_id=campaign_id, **payload.model_dump())
    session.add(npc)
    await session.commit()
    await session.refresh(npc)
    return npc


@router.get("", response_model=list[NPCOut])
async def list_npcs(
    campaign_id: str, session: AsyncSession = Depends(db_session)
) -> list[NPC]:
    rows = (
        await session.execute(select(NPC).where(NPC.campaign_id == campaign_id))
    ).scalars().all()
    return list(rows)


@router.get("/{npc_id}", response_model=NPCOut)
async def get_npc(
    campaign_id: str, npc_id: str, session: AsyncSession = Depends(db_session)
) -> NPC:
    npc = await session.get(NPC, npc_id)
    if npc is None or npc.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="NPC not found")
    return npc


@router.patch("/{npc_id}", response_model=NPCOut)
async def update_npc(
    campaign_id: str,
    npc_id: str,
    payload: NPCUpdate,
    session: AsyncSession = Depends(db_session),
) -> NPC:
    npc = await session.get(NPC, npc_id)
    if npc is None or npc.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="NPC not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(npc, field, value)
    await session.commit()
    await session.refresh(npc)
    return npc


@router.delete("/{npc_id}")
async def delete_npc(
    campaign_id: str, npc_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    npc = await session.get(NPC, npc_id)
    if npc is None or npc.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="NPC not found")
    await session.delete(npc)
    await session.commit()
    return {"deleted": npc_id}
