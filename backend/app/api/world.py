"""World simulation API: factions and world events."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.api.schemas import (
    FactionCreate,
    FactionOut,
    FactionUpdate,
    WorldEventCreate,
    WorldEventOut,
)
from app.db.models import Campaign, Faction, WorldEvent
from app.world.faction_engine import FactionEngine

router = APIRouter(prefix="/api/campaigns/{campaign_id}", tags=["world"])


async def _get_campaign(session: AsyncSession, campaign_id: str) -> Campaign:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


# --------------------------- Factions --------------------------- #
@router.get("/factions", response_model=list[FactionOut])
async def list_factions(
    campaign_id: str, session: AsyncSession = Depends(db_session)
) -> list[Faction]:
    await _get_campaign(session, campaign_id)
    rows = (
        await session.execute(
            select(Faction)
            .where(Faction.campaign_id == campaign_id)
            .order_by(Faction.created_at.asc())
        )
    ).scalars().all()
    return list(rows)


@router.post("/factions", response_model=FactionOut)
async def create_faction(
    campaign_id: str,
    payload: FactionCreate,
    session: AsyncSession = Depends(db_session),
) -> Faction:
    await _get_campaign(session, campaign_id)
    faction = Faction(campaign_id=campaign_id, **payload.model_dump())
    session.add(faction)
    await session.commit()
    await session.refresh(faction)
    return faction


@router.patch("/factions/{faction_id}", response_model=FactionOut)
async def update_faction(
    campaign_id: str,
    faction_id: str,
    payload: FactionUpdate,
    session: AsyncSession = Depends(db_session),
) -> Faction:
    faction = await session.get(Faction, faction_id)
    if faction is None or faction.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Faction not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(faction, field, value)
    await session.commit()
    await session.refresh(faction)
    return faction


@router.delete("/factions/{faction_id}")
async def delete_faction(
    campaign_id: str,
    faction_id: str,
    session: AsyncSession = Depends(db_session),
) -> dict:
    faction = await session.get(Faction, faction_id)
    if faction is None or faction.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Faction not found")
    await session.delete(faction)
    await session.commit()
    return {"deleted": faction_id}


# --------------------------- World Events --------------------------- #
@router.get("/world-events", response_model=list[WorldEventOut])
async def list_world_events(
    campaign_id: str,
    revealed: bool | None = None,
    session: AsyncSession = Depends(db_session),
) -> list[WorldEvent]:
    await _get_campaign(session, campaign_id)
    stmt = select(WorldEvent).where(WorldEvent.campaign_id == campaign_id)
    if revealed is not None:
        stmt = stmt.where(WorldEvent.is_revealed == revealed)
    stmt = stmt.order_by(WorldEvent.created_at.desc())
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


@router.post("/world-events", response_model=WorldEventOut)
async def create_world_event(
    campaign_id: str,
    payload: WorldEventCreate,
    session: AsyncSession = Depends(db_session),
) -> WorldEvent:
    await _get_campaign(session, campaign_id)
    event = WorldEvent(campaign_id=campaign_id, **payload.model_dump())
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


@router.patch("/world-events/{event_id}", response_model=WorldEventOut)
async def reveal_world_event(
    campaign_id: str,
    event_id: str,
    is_revealed: bool = True,
    session: AsyncSession = Depends(db_session),
) -> WorldEvent:
    event = await session.get(WorldEvent, event_id)
    if event is None or event.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="World event not found")
    event.is_revealed = is_revealed
    await session.commit()
    await session.refresh(event)
    return event


# --------------------------- Autonomy Tick --------------------------- #
@router.post("/world/tick", response_model=list[WorldEventOut])
async def tick_world(
    campaign_id: str,
    force: bool = True,
    session: AsyncSession = Depends(db_session),
) -> list[WorldEvent]:
    """Manually advance the world: run one faction autonomy cycle."""
    await _get_campaign(session, campaign_id)
    engine = FactionEngine(session)
    return await engine.tick(campaign_id, force=force)
