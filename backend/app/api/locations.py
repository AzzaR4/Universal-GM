"""Location CRUD within a campaign."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.api.schemas import LocationCreate, LocationOut, LocationUpdate
from app.db.models import Campaign, Location

router = APIRouter(prefix="/api/campaigns/{campaign_id}/locations", tags=["locations"])


@router.post("", response_model=LocationOut)
async def create_location(
    campaign_id: str,
    payload: LocationCreate,
    session: AsyncSession = Depends(db_session),
) -> Location:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    location = Location(campaign_id=campaign_id, **payload.model_dump())
    session.add(location)
    await session.flush()
    # If the campaign has no current location, set this as the starting one.
    if not campaign.current_location_id:
        campaign.current_location_id = location.id
    await session.commit()
    await session.refresh(location)
    return location


@router.get("", response_model=list[LocationOut])
async def list_locations(
    campaign_id: str, session: AsyncSession = Depends(db_session)
) -> list[Location]:
    rows = (
        await session.execute(select(Location).where(Location.campaign_id == campaign_id))
    ).scalars().all()
    return list(rows)


@router.get("/{location_id}", response_model=LocationOut)
async def get_location(
    campaign_id: str, location_id: str, session: AsyncSession = Depends(db_session)
) -> Location:
    location = await session.get(Location, location_id)
    if location is None or location.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Location not found")
    return location


@router.patch("/{location_id}", response_model=LocationOut)
async def update_location(
    campaign_id: str,
    location_id: str,
    payload: LocationUpdate,
    session: AsyncSession = Depends(db_session),
) -> Location:
    location = await session.get(Location, location_id)
    if location is None or location.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Location not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(location, field, value)
    await session.commit()
    await session.refresh(location)
    return location


@router.delete("/{location_id}")
async def delete_location(
    campaign_id: str, location_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    location = await session.get(Location, location_id)
    if location is None or location.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Location not found")
    await session.delete(location)
    await session.commit()
    return {"deleted": location_id}
