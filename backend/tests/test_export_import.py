"""Round-trip export/import tests (no HTTP layer, calls the handlers directly)."""
from __future__ import annotations

import pytest

from app.api.export import export_campaign, import_campaign
from app.db.models import Campaign, Character, Location, NPC, Quest

pytestmark = pytest.mark.asyncio


async def _seed_full(session):
    campaign = Campaign(
        name="Saga", description="epic", ruleset_id="generic",
        ruleset_config={"resolution_mode": "rules_light"}, gm_config={"difficulty": 3},
    )
    session.add(campaign)
    await session.flush()
    loc = Location(campaign_id=campaign.id, name="Tavern", atmosphere="cozy")
    session.add(loc)
    await session.flush()
    campaign.current_location_id = loc.id
    char = Character(
        campaign_id=campaign.id, name="Rogue", is_player_character=True,
        ruleset_data={"resources": {"Health": {"current": 8, "max": 10}}},
        location_id=loc.id, conditions=["Wounded"], inventory=["dagger"],
    )
    npc = NPC(
        campaign_id=campaign.id, name="Barkeep", personality={"trait": "gruff"},
        location_id=loc.id, current_activity="cleaning mugs",
    )
    quest = Quest(campaign_id=campaign.id, title="Find the ring", status="active")
    session.add_all([char, npc, quest])
    await session.commit()
    return campaign


async def test_export_contains_all_entities(session):
    campaign = await _seed_full(session)
    data = await export_campaign(campaign.id, session)
    assert data["export_version"] == 1
    assert data["campaign"]["name"] == "Saga"
    assert len(data["characters"]) == 1
    assert len(data["npcs"]) == 1
    assert len(data["locations"]) == 1
    assert len(data["quests"]) == 1


async def test_round_trip_import_creates_new_campaign(session):
    campaign = await _seed_full(session)
    exported = await export_campaign(campaign.id, session)

    result = await import_campaign(exported, session)
    assert result["imported"] is True
    new_id = result["campaign_id"]
    assert new_id != campaign.id

    # Re-export the imported campaign and compare structure.
    reexported = await export_campaign(new_id, session)
    assert reexported["campaign"]["name"] == exported["campaign"]["name"]
    assert reexported["campaign"]["description"] == exported["campaign"]["description"]
    assert reexported["campaign"]["ruleset_config"] == exported["campaign"]["ruleset_config"]
    assert len(reexported["characters"]) == len(exported["characters"])
    assert len(reexported["npcs"]) == len(exported["npcs"])
    assert len(reexported["locations"]) == len(exported["locations"])

    # Relationship integrity: the imported character points at the imported location.
    new_char = reexported["characters"][0]
    new_loc_id = reexported["locations"][0]["id"]
    assert new_char["location_id"] == new_loc_id
    # current_location_id remapped correctly.
    assert reexported["campaign"]["current_location_id"] == new_loc_id


async def test_import_preserves_character_details(session):
    campaign = await _seed_full(session)
    exported = await export_campaign(campaign.id, session)
    result = await import_campaign(exported, session)
    reexported = await export_campaign(result["campaign_id"], session)
    char = reexported["characters"][0]
    assert char["name"] == "Rogue"
    assert char["conditions"] == ["Wounded"]
    assert char["inventory"] == ["dagger"]
    assert char["ruleset_data"]["resources"]["Health"]["current"] == 8


async def test_import_invalid_payload_raises(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await import_campaign({"not_a_campaign": True}, session)
