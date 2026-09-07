"""Character CRUD within a campaign."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.api.schemas import CharacterCreate, CharacterOut, CharacterUpdate
from app.db.models import Campaign, Character
from app.rulesets.registry import get_ruleset

router = APIRouter(prefix="/api/campaigns/{campaign_id}/characters", tags=["characters"])


@router.post("", response_model=CharacterOut)
async def create_character(
    campaign_id: str,
    payload: CharacterCreate,
    session: AsyncSession = Depends(db_session),
) -> Character:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    ruleset_data = payload.ruleset_data
    if not ruleset_data:
        ruleset = get_ruleset(campaign.ruleset_id)
        ruleset_data = ruleset.new_character_data(campaign.ruleset_config or {})

    location_id = payload.location_id or campaign.current_location_id
    character = Character(
        campaign_id=campaign_id,
        name=payload.name,
        description=payload.description,
        is_player_character=payload.is_player_character,
        ruleset_data=ruleset_data,
        conditions=payload.conditions,
        inventory=payload.inventory,
        location_id=location_id,
    )
    session.add(character)
    await session.commit()
    await session.refresh(character)
    return character


@router.get("", response_model=list[CharacterOut])
async def list_characters(
    campaign_id: str, session: AsyncSession = Depends(db_session)
) -> list[Character]:
    rows = (
        await session.execute(
            select(Character).where(Character.campaign_id == campaign_id)
        )
    ).scalars().all()
    return list(rows)


@router.get("/{character_id}", response_model=CharacterOut)
async def get_character(
    campaign_id: str, character_id: str, session: AsyncSession = Depends(db_session)
) -> Character:
    character = await session.get(Character, character_id)
    if character is None or character.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.patch("/{character_id}", response_model=CharacterOut)
async def update_character(
    campaign_id: str,
    character_id: str,
    payload: CharacterUpdate,
    session: AsyncSession = Depends(db_session),
) -> Character:
    character = await session.get(Character, character_id)
    if character is None or character.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Character not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(character, field, value)
    await session.commit()
    await session.refresh(character)
    return character


@router.delete("/{character_id}")
async def delete_character(
    campaign_id: str, character_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    character = await session.get(Character, character_id)
    if character is None or character.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Character not found")
    await session.delete(character)
    await session.commit()
    return {"deleted": character_id}
