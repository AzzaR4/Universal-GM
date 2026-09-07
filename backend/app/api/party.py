"""Party management: which player characters are in a campaign's active party.

The party is tracked via the PartyMember association table so a character can
exist in a campaign "library" before being formally added to the active party.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.api.schemas import CharacterOut
from app.db.models import Campaign, Character, PartyMember
from app.rulesets.registry import get_ruleset

router = APIRouter(prefix="/api/campaigns/{campaign_id}/party", tags=["party"])
# Ruleset character-schema lives on its own prefix (not campaign-scoped).
schema_router = APIRouter(prefix="/api/rulesets", tags=["party"])


@router.get("", response_model=list[CharacterOut])
async def list_party(
    campaign_id: str, session: AsyncSession = Depends(db_session)
) -> list[Character]:
    """Return the campaign's active party (PCs enrolled via PartyMember)."""
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    rows = (
        await session.execute(
            select(Character)
            .join(PartyMember, PartyMember.character_id == Character.id)
            .where(PartyMember.campaign_id == campaign_id)
            .order_by(PartyMember.joined_at.asc())
        )
    ).scalars().all()
    return list(rows)


@router.post("/{character_id}", response_model=list[CharacterOut])
async def add_to_party(
    campaign_id: str,
    character_id: str,
    session: AsyncSession = Depends(db_session),
) -> list[Character]:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    character = await session.get(Character, character_id)
    if character is None or character.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Character not found")

    existing = await session.get(PartyMember, (campaign_id, character_id))
    if existing is None:
        session.add(PartyMember(campaign_id=campaign_id, character_id=character_id))
        await session.commit()

    return await list_party(campaign_id, session)


@router.delete("/{character_id}")
async def remove_from_party(
    campaign_id: str,
    character_id: str,
    session: AsyncSession = Depends(db_session),
) -> dict:
    member = await session.get(PartyMember, (campaign_id, character_id))
    if member is None:
        raise HTTPException(status_code=404, detail="Character not in party")
    await session.delete(member)
    await session.commit()
    return {"removed": character_id}


@schema_router.get("/{ruleset_id}/character-schema")
async def get_character_schema(
    ruleset_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    """Return the ruleset's attribute/resource/skill schema for the creation wizard.

    Works for both built-in and (dynamically registered) custom rulesets.
    """
    try:
        rs = get_ruleset(ruleset_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc))
    schema = rs.character_schema()
    return {
        "id": rs.id,
        "name": rs.name,
        "description": rs.description,
        "schema": schema,
        # Also flatten for convenience so the wizard can read either shape.
        **schema,
    }
