"""Tests for the combat system: initiative, turns, damage, defeat detection."""
from __future__ import annotations

import pytest

from app.db.models import Campaign, Character, NPC
from app.game.state.combat_state import CombatState, Combatant
from app.game.state.state_manager import StateManager


# --------------------------------------------------------------------------- #
# Pure CombatState unit tests (no DB).
# --------------------------------------------------------------------------- #
def _combat() -> CombatState:
    return CombatState(
        combatants=[
            Combatant(id="pc1", name="Hero", is_player=True, initiative=15, hp_current=10, hp_max=10),
            Combatant(id="npc1", name="Goblin", is_player=False, initiative=8, hp_current=6,
                      hp_max=6, is_npc=True),
            Combatant(id="npc2", name="Wolf", is_player=False, initiative=20, hp_current=4,
                      hp_max=4, is_npc=True),
        ]
    )


def test_initiative_ordering_is_descending():
    combat = _combat()
    order = [c.name for c in combat.order()]
    assert order == ["Wolf", "Hero", "Goblin"]
    assert combat.current_combatant().name == "Wolf"


def test_advance_turn_wraps_and_increments_round():
    combat = _combat()
    assert combat.round == 1
    combat.advance_turn()  # Wolf -> Hero
    assert combat.current_combatant().name == "Hero"
    combat.advance_turn()  # Hero -> Goblin
    assert combat.current_combatant().name == "Goblin"
    combat.advance_turn()  # wrap -> Wolf, round 2
    assert combat.current_combatant().name == "Wolf"
    assert combat.round == 2


def test_advance_turn_skips_defeated():
    combat = _combat()
    combat.get("pc1").status = "defeated"  # Hero out
    combat.advance_turn()  # Wolf -> (skip Hero) -> Goblin
    assert combat.current_combatant().name == "Goblin"


def test_is_over_when_one_side_down():
    combat = _combat()
    assert combat.is_over() is False
    combat.get("npc1").status = "defeated"
    combat.get("npc2").status = "defeated"
    assert combat.is_over() is True


def test_serialisation_roundtrip():
    combat = _combat()
    data = combat.to_dict()
    assert data["current_id"] == "npc2"
    restored = CombatState.from_dict(data)
    assert restored is not None
    assert len(restored.combatants) == 3
    assert restored.order()[0].name == "Wolf"


# --------------------------------------------------------------------------- #
# DB-backed StateManager combat tests.
# --------------------------------------------------------------------------- #
async def _seed(session) -> str:
    campaign = Campaign(name="Combat Test", ruleset_id="generic", ruleset_config={},
                        gm_config={}, world_state={})
    session.add(campaign)
    await session.flush()
    pc = Character(
        campaign_id=campaign.id, name="Hero", is_player_character=True,
        ruleset_data={"attributes": {"Agility": 7},
                      "resources": {"Health": {"current": 10, "max": 10}}},
        location_id="loc1", status="alive",
    )
    npc = NPC(campaign_id=campaign.id, name="Bandit", location_id="loc1", status="alive")
    session.add_all([pc, npc])
    campaign.current_location_id = "loc1"
    await session.commit()
    return campaign.id


@pytest.mark.asyncio
async def test_start_combat_builds_combatants(session):
    campaign_id = await _seed(session)
    manager = StateManager(session)
    combat = await manager.start_combat(campaign_id, default_enemy_hp=8)
    assert combat.active is True
    names = {c.name for c in combat.combatants}
    assert "Hero" in names and "Bandit" in names
    hero = next(c for c in combat.combatants if c.name == "Hero")
    assert hero.is_player is True
    assert hero.initiative == 7  # generic get_initiative uses Agility
    bandit = next(c for c in combat.combatants if c.name == "Bandit")
    assert bandit.hp_max == 8 and bandit.is_npc is True


@pytest.mark.asyncio
async def test_apply_combat_action_damages_and_advances(session):
    campaign_id = await _seed(session)
    manager = StateManager(session)
    combat = await manager.start_combat(campaign_id, default_enemy_hp=8)
    bandit = next(c for c in combat.combatants if c.name == "Bandit")
    combat2 = await manager.apply_combat_action(
        campaign_id, actor_id=None, target_id=bandit.id, damage=3, end_turn=True
    )
    updated = combat2.get(bandit.id)
    assert updated.hp_current == 5


@pytest.mark.asyncio
async def test_apply_combat_action_defeats_and_ends(session):
    campaign_id = await _seed(session)
    manager = StateManager(session)
    combat = await manager.start_combat(campaign_id, default_enemy_hp=5)
    bandit = next(c for c in combat.combatants if c.name == "Bandit")
    combat2 = await manager.apply_combat_action(
        campaign_id, actor_id=None, target_id=bandit.id, damage=99, end_turn=True
    )
    assert combat2.get(bandit.id).status == "defeated"
    # With no enemies left, combat is over and marked inactive.
    assert combat2.is_over() is True
    assert combat2.active is False


@pytest.mark.asyncio
async def test_player_damage_syncs_to_character(session):
    campaign_id = await _seed(session)
    manager = StateManager(session)
    combat = await manager.start_combat(campaign_id, default_enemy_hp=8)
    hero = next(c for c in combat.combatants if c.name == "Hero")
    await manager.apply_combat_action(
        campaign_id, actor_id=None, target_id=hero.id, damage=4, end_turn=False
    )
    # Reload state and confirm the character's Health resource dropped.
    state = await manager.load(campaign_id)
    pc = state.get_player_character()
    assert pc.ruleset_data["resources"]["Health"]["current"] == 6


@pytest.mark.asyncio
async def test_end_combat_clears_state(session):
    campaign_id = await _seed(session)
    manager = StateManager(session)
    await manager.start_combat(campaign_id)
    await manager.end_combat(campaign_id)
    assert await manager.get_combat(campaign_id) is None
