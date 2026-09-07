"""Tests for the Generic ruleset validation and resolution."""
from __future__ import annotations

import random

import pytest

from app.core.exceptions import RuleViolationError
from app.game.rules.base_ruleset import ActionIntent
from app.game.state.game_state import CharacterView, GameState, NPCView, LocationView
from app.rulesets.generic.ruleset import GenericRuleset
from app.rulesets.generic.schema import GenericRulesetConfig


def make_state(resolution_mode: str = "rules_light") -> GameState:
    config = GenericRulesetConfig(resolution_mode=resolution_mode).model_dump()
    pc = CharacterView(
        id="pc1",
        name="Hero",
        description="A brave adventurer",
        is_player_character=True,
        ruleset_data={"resources": {"Health": {"current": 10, "max": 10}}},
        conditions=[],
        inventory=[],
        location_id="loc1",
        status="alive",
    )
    npc = NPCView(
        id="npc1", name="Goblin", description="A snarling goblin",
        location_id="loc1", current_activity="lurking", status="alive",
    )
    loc = LocationView(id="loc1", name="Cave", description="dark", atmosphere="damp")
    loc2 = LocationView(id="loc2", name="Forest", description="green", atmosphere="misty")
    return GameState(
        campaign_id="c1",
        campaign_name="Test",
        ruleset_id="generic",
        ruleset_config=config,
        gm_config={},
        current_location_id="loc1",
        characters=[pc],
        npcs=[npc],
        locations=[loc, loc2],
    )


def test_default_config_and_schema():
    rs = GenericRuleset()
    cfg = rs.default_config()
    assert cfg["resolution_mode"] == "rules_light"
    assert cfg["default_dice"] == "2d6"
    schema = rs.character_schema()
    assert "attributes" in schema and "resources" in schema


def test_new_character_data():
    rs = GenericRuleset()
    data = rs.new_character_data({})
    assert "Health" in data["resources"]
    assert data["resources"]["Health"]["current"] == 10


def test_validate_dead_character_cannot_act():
    rs = GenericRuleset()
    state = make_state()
    state.characters[0].status = "defeated"
    intent = ActionIntent(action_type="attack", actor_id="pc1", target_id="npc1")
    with pytest.raises(RuleViolationError):
        rs.validate_action(intent, state)


def test_validate_invalid_move_target():
    rs = GenericRuleset()
    state = make_state()
    intent = ActionIntent(action_type="move", actor_id="pc1", target_location_id="does_not_exist")
    with pytest.raises(RuleViolationError):
        rs.validate_action(intent, state)


def test_resolve_move_no_check_produces_move_mutation():
    rs = GenericRuleset()
    state = make_state()
    intent = ActionIntent(action_type="move", actor_id="pc1", target_location_id="loc2")
    result = rs.resolve_action(intent, state)
    assert result.check_required is False
    assert any(m.kind == "move" for m in result.state_mutations)


def test_resolve_attack_requires_check_and_may_damage():
    rs = GenericRuleset()
    state = make_state()
    intent = ActionIntent(action_type="attack", actor_id="pc1", target_id="npc1")
    # Force a high roll for a success by seeding RNG.
    result = rs.resolve_action(intent, state, rng=random.Random(1))
    assert result.check_required is True
    assert result.dice_rolled is not None
    assert result.outcome in {
        "critical_success", "success", "partial", "failure", "critical_failure"
    }


def test_outcome_mapping():
    rs = GenericRuleset()
    assert rs._map_outcome(12) == "critical_success"
    assert rs._map_outcome(11) == "success"
    assert rs._map_outcome(8) == "success"
    assert rs._map_outcome(7) == "partial"
    assert rs._map_outcome(5) == "partial"
    assert rs._map_outcome(4) == "failure"
    assert rs._map_outcome(3) == "failure"
    assert rs._map_outcome(2) == "critical_failure"


def test_narrative_only_mode_never_rolls():
    rs = GenericRuleset()
    state = make_state(resolution_mode="narrative_only")
    intent = ActionIntent(action_type="attack", actor_id="pc1", target_id="npc1")
    result = rs.resolve_action(intent, state)
    assert result.check_required is False
    assert result.dice_rolled is None


def test_successful_attack_generates_damage_mutation():
    rs = GenericRuleset()
    state = make_state()
    intent = ActionIntent(action_type="attack", actor_id="pc1", target_id="npc1")
    # Find a seed that yields success (total >= 8) and check damage mutation exists.
    found = False
    for seed in range(100):
        result = rs.resolve_action(intent, state, rng=random.Random(seed))
        if result.outcome in {"success", "critical_success", "partial"}:
            assert any(m.kind == "damage" for m in result.state_mutations)
            found = True
            break
    assert found


def test_system_prompt_fragment():
    rs = GenericRuleset()
    state = make_state()
    prompt = rs.system_prompt_fragment(state)
    assert "Game Master" in prompt
