"""Tests for GameState loading and mutation application via StateManager."""
from __future__ import annotations

import pytest

from app.db.models import Campaign, Character, Location
from app.game.state.game_state import (
    AddConditionMutation,
    DamageMutation,
    HealMutation,
    MoveMutation,
)
from app.game.state.state_manager import StateManager

pytestmark = pytest.mark.asyncio


async def _seed(session):
    campaign = Campaign(name="C", ruleset_id="generic", ruleset_config={}, gm_config={})
    session.add(campaign)
    await session.flush()
    loc1 = Location(campaign_id=campaign.id, name="Start")
    loc2 = Location(campaign_id=campaign.id, name="Dungeon")
    session.add_all([loc1, loc2])
    await session.flush()
    campaign.current_location_id = loc1.id
    char = Character(
        campaign_id=campaign.id,
        name="Hero",
        is_player_character=True,
        ruleset_data={"resources": {"Health": {"current": 10, "max": 10}}},
        location_id=loc1.id,
    )
    session.add(char)
    await session.commit()
    return campaign, char, loc1, loc2


async def test_load_game_state(session):
    campaign, char, loc1, _ = await _seed(session)
    sm = StateManager(session)
    state = await sm.load(campaign.id)
    assert state.campaign_id == campaign.id
    assert len(state.characters) == 1
    assert state.get_player_character().name == "Hero"
    assert len(state.locations) == 2


async def test_apply_damage_mutation(session):
    campaign, char, _, _ = await _seed(session)
    sm = StateManager(session)
    applied = await sm.apply_mutations(
        campaign.id, [DamageMutation(character_id=char.id, resource="Health", amount=4)]
    )
    assert applied[0]["new_value"] == 6
    await session.refresh(char)
    assert char.ruleset_data["resources"]["Health"]["current"] == 6


async def test_damage_to_zero_sets_defeated(session):
    campaign, char, _, _ = await _seed(session)
    sm = StateManager(session)
    await sm.apply_mutations(
        campaign.id, [DamageMutation(character_id=char.id, resource="Health", amount=50)]
    )
    await session.refresh(char)
    assert char.ruleset_data["resources"]["Health"]["current"] == 0
    assert char.status == "defeated"


async def test_heal_does_not_exceed_max(session):
    campaign, char, _, _ = await _seed(session)
    sm = StateManager(session)
    await sm.apply_mutations(
        campaign.id, [DamageMutation(character_id=char.id, resource="Health", amount=5)]
    )
    await sm.apply_mutations(
        campaign.id, [HealMutation(character_id=char.id, resource="Health", amount=100)]
    )
    await session.refresh(char)
    assert char.ruleset_data["resources"]["Health"]["current"] == 10


async def test_move_mutation_updates_location(session):
    campaign, char, loc1, loc2 = await _seed(session)
    sm = StateManager(session)
    await sm.apply_mutations(
        campaign.id, [MoveMutation(character_id=char.id, to_location_id=loc2.id)]
    )
    await session.refresh(char)
    await session.refresh(campaign)
    assert char.location_id == loc2.id
    assert campaign.current_location_id == loc2.id


async def test_add_condition_mutation(session):
    campaign, char, _, _ = await _seed(session)
    sm = StateManager(session)
    await sm.apply_mutations(
        campaign.id, [AddConditionMutation(character_id=char.id, condition="Wounded")]
    )
    await session.refresh(char)
    assert "Wounded" in char.conditions
