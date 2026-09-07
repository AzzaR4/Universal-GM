"""Campaign export / import as versioned JSON."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.db.models import (
    Campaign,
    Character,
    EventLog,
    Item,
    Location,
    Memory,
    NPC,
    Quest,
)

router = APIRouter(prefix="/api/campaigns", tags=["export"])

EXPORT_VERSION = 1


def _row_to_dict(row: Any, fields: list[str]) -> dict:
    return {f: getattr(row, f) for f in fields}


CAMPAIGN_FIELDS = [
    "id", "name", "description", "ruleset_id", "campaign_style", "narrative_style",
    "gm_config", "ruleset_config", "world_state", "current_location_id", "is_active",
]
CHARACTER_FIELDS = [
    "id", "campaign_id", "name", "description", "is_player_character", "ruleset_data",
    "conditions", "inventory", "location_id", "status",
]
NPC_FIELDS = [
    "id", "campaign_id", "name", "description", "personality", "goals", "knowledge",
    "secrets", "relationships", "location_id", "current_activity", "status",
]
LOCATION_FIELDS = [
    "id", "campaign_id", "name", "description", "atmosphere", "connected_location_ids",
    "is_discovered", "lore",
]
ITEM_FIELDS = [
    "id", "campaign_id", "name", "description", "item_type", "ruleset_data",
    "owner_id", "location_id", "is_destroyed",
]
QUEST_FIELDS = ["id", "campaign_id", "title", "description", "status", "objectives", "notes"]
MEMORY_FIELDS = [
    "id", "campaign_id", "memory_type", "subject_id", "content", "importance", "keywords",
]


async def _fetch(session: AsyncSession, model, campaign_id: str):
    return (
        await session.execute(select(model).where(model.campaign_id == campaign_id))
    ).scalars().all()


@router.get("/{campaign_id}/export")
async def export_campaign(
    campaign_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    return {
        "export_version": EXPORT_VERSION,
        "campaign": _row_to_dict(campaign, CAMPAIGN_FIELDS),
        "characters": [_row_to_dict(r, CHARACTER_FIELDS) for r in await _fetch(session, Character, campaign_id)],
        "npcs": [_row_to_dict(r, NPC_FIELDS) for r in await _fetch(session, NPC, campaign_id)],
        "locations": [_row_to_dict(r, LOCATION_FIELDS) for r in await _fetch(session, Location, campaign_id)],
        "items": [_row_to_dict(r, ITEM_FIELDS) for r in await _fetch(session, Item, campaign_id)],
        "quests": [_row_to_dict(r, QUEST_FIELDS) for r in await _fetch(session, Quest, campaign_id)],
        "memories": [_row_to_dict(r, MEMORY_FIELDS) for r in await _fetch(session, Memory, campaign_id)],
    }


@router.post("/import")
async def import_campaign(
    payload: dict, session: AsyncSession = Depends(db_session)
) -> dict:
    if not isinstance(payload, dict) or "campaign" not in payload:
        raise HTTPException(status_code=422, detail="Invalid export file: missing 'campaign'.")

    camp_data = dict(payload["campaign"])
    # Remap IDs so imports never collide with existing rows.
    id_map: dict[str, str] = {}

    def new_id(old: str | None) -> str | None:
        if not old:
            return old
        if old not in id_map:
            id_map[old] = str(uuid.uuid4())
        return id_map[old]

    old_campaign_id = camp_data.get("id")
    new_campaign_id = new_id(old_campaign_id)

    # Pre-map location ids so references resolve.
    for loc in payload.get("locations", []):
        new_id(loc.get("id"))
    for ch in payload.get("characters", []):
        new_id(ch.get("id"))
    for npc in payload.get("npcs", []):
        new_id(npc.get("id"))

    campaign = Campaign(
        id=new_campaign_id,
        name=camp_data.get("name", "Imported Campaign"),
        description=camp_data.get("description", ""),
        ruleset_id=camp_data.get("ruleset_id", "generic"),
        campaign_style=camp_data.get("campaign_style", ""),
        narrative_style=camp_data.get("narrative_style", ""),
        gm_config=camp_data.get("gm_config", {}),
        ruleset_config=camp_data.get("ruleset_config", {}),
        world_state=camp_data.get("world_state", {}),
        current_location_id=new_id(camp_data.get("current_location_id")),
        is_active=camp_data.get("is_active", True),
    )
    session.add(campaign)

    for loc in payload.get("locations", []):
        session.add(Location(
            id=new_id(loc.get("id")),
            campaign_id=new_campaign_id,
            name=loc.get("name", ""),
            description=loc.get("description", ""),
            atmosphere=loc.get("atmosphere", ""),
            connected_location_ids=[new_id(x) for x in loc.get("connected_location_ids", [])],
            is_discovered=loc.get("is_discovered", True),
            lore=loc.get("lore", {}),
        ))

    for ch in payload.get("characters", []):
        session.add(Character(
            id=new_id(ch.get("id")),
            campaign_id=new_campaign_id,
            name=ch.get("name", ""),
            description=ch.get("description", ""),
            is_player_character=ch.get("is_player_character", True),
            ruleset_data=ch.get("ruleset_data", {}),
            conditions=ch.get("conditions", []),
            inventory=ch.get("inventory", []),
            location_id=new_id(ch.get("location_id")),
            status=ch.get("status", "alive"),
        ))

    for npc in payload.get("npcs", []):
        session.add(NPC(
            id=new_id(npc.get("id")),
            campaign_id=new_campaign_id,
            name=npc.get("name", ""),
            description=npc.get("description", ""),
            personality=npc.get("personality", {}),
            goals=npc.get("goals", []),
            knowledge=npc.get("knowledge", []),
            secrets=npc.get("secrets", []),
            relationships=npc.get("relationships", {}),
            location_id=new_id(npc.get("location_id")),
            current_activity=npc.get("current_activity", ""),
            status=npc.get("status", "alive"),
        ))

    for it in payload.get("items", []):
        session.add(Item(
            id=new_id(it.get("id")),
            campaign_id=new_campaign_id,
            name=it.get("name", ""),
            description=it.get("description", ""),
            item_type=it.get("item_type", "misc"),
            ruleset_data=it.get("ruleset_data", {}),
            owner_id=new_id(it.get("owner_id")),
            location_id=new_id(it.get("location_id")),
            is_destroyed=it.get("is_destroyed", False),
        ))

    for q in payload.get("quests", []):
        session.add(Quest(
            id=new_id(q.get("id")),
            campaign_id=new_campaign_id,
            title=q.get("title", ""),
            description=q.get("description", ""),
            status=q.get("status", "active"),
            objectives=q.get("objectives", []),
            notes=q.get("notes", ""),
        ))

    for m in payload.get("memories", []):
        session.add(Memory(
            id=new_id(m.get("id")),
            campaign_id=new_campaign_id,
            memory_type=m.get("memory_type", "event"),
            subject_id=new_id(m.get("subject_id")),
            content=m.get("content", ""),
            importance=m.get("importance", 0.5),
            keywords=m.get("keywords", []),
        ))

    await session.commit()
    return {"imported": True, "campaign_id": new_campaign_id}
