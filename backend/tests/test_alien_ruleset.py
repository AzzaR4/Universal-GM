"""Tests for the Alien RPG-style ruleset (Year Zero Engine)."""
from __future__ import annotations

import random

import pytest

from app.core.exceptions import RuleViolationError
from app.game.rules.base_ruleset import ActionIntent
from app.game.state.game_state import CharacterView, GameState, LocationView, NPCView
from app.rulesets.alien_rpg.ruleset import AlienRPGRuleset


def make_state(pc_data=None) -> GameState:
    rs = AlienRPGRuleset()
    data = pc_data or rs.new_character_data({})
    pc = CharacterView(
        id="pc1", name="Ripley", description="A warrant officer", is_player_character=True,
        ruleset_data=data, conditions=[], inventory=[], location_id="loc1", status="alive",
    )
    npc = NPCView(id="npc1", name="Xeno", description="A creature",
                  location_id="loc1", current_activity="stalking", status="alive")
    loc = LocationView(id="loc1", name="Deck C", description="dark", atmosphere="dread")
    loc2 = LocationView(id="loc2", name="Airlock", description="cold", atmosphere="tense")
    return GameState(
        campaign_id="c1", campaign_name="T", ruleset_id="alien_rpg",
        ruleset_config=rs.default_config(), gm_config={}, current_location_id="loc1",
        characters=[pc], npcs=[npc], locations=[loc, loc2],
    )


def test_default_config_and_character():
    rs = AlienRPGRuleset()
    cfg = rs.default_config()
    assert cfg["success_on"] == 6
    data = rs.new_character_data(cfg)
    assert "Health" in data["resources"]
    assert "Stress" in data["resources"]
    assert data["panic_level"] == 0


def test_schema_has_attributes_and_skills():
    rs = AlienRPGRuleset()
    schema = rs.character_schema()
    assert len(schema["attributes"]) == 4
    assert any(s["name"] == "Ranged Combat" for s in schema["skills"])


def test_validate_dead_actor():
    rs = AlienRPGRuleset()
    state = make_state()
    state.characters[0].status = "defeated"
    intent = ActionIntent(action_type="skill_check", actor_id="pc1")
    with pytest.raises(RuleViolationError):
        rs.validate_action(intent, state)


def test_pool_counts_sixes_as_successes():
    rs = AlienRPGRuleset()
    state = make_state()
    intent = ActionIntent(action_type="skill_check", actor_id="pc1",
                          metadata={"pool": 8})
    # Across seeds, at least one roll should succeed and one should fail.
    outcomes = set()
    for seed in range(100):
        result = rs.resolve_action(intent, state, rng=random.Random(seed))
        outcomes.add(result.outcome)
        d = result.dice_rolled
        assert d["successes"] == sum(1 for r in d["rolls"] if r == 6)
    assert "success" in outcomes
    assert "failure" in outcomes


def test_push_adds_stress_and_dice():
    rs = AlienRPGRuleset()
    # Give the character some existing stress so a stress die exists.
    data = rs.new_character_data({})
    data["resources"]["Stress"]["current"] = 1
    state = make_state(pc_data=data)
    intent = ActionIntent(action_type="skill_check", actor_id="pc1",
                          metadata={"pool": 4, "push": True})
    result = rs.resolve_action(intent, state, rng=random.Random(5))
    d = result.dice_rolled
    assert d["pushed"] is True
    # Pushing raises stress -> a heal mutation on the Stress resource.
    assert any(m.kind == "heal" and m.resource == "Stress" for m in result.state_mutations)


def test_panic_risk_on_stress_bane():
    rs = AlienRPGRuleset()
    data = rs.new_character_data({})
    data["resources"]["Stress"]["current"] = 5
    state = make_state(pc_data=data)
    intent = ActionIntent(action_type="skill_check", actor_id="pc1",
                          metadata={"pool": 2})
    found_panic = False
    for seed in range(100):
        result = rs.resolve_action(intent, state, rng=random.Random(seed))
        if result.dice_rolled["panic"]:
            assert any(m.kind == "add_condition" and m.condition == "Panicking"
                       for m in result.state_mutations)
            found_panic = True
            break
    assert found_panic


def test_attack_damage_on_success():
    rs = AlienRPGRuleset()
    state = make_state()
    intent = ActionIntent(action_type="attack", actor_id="pc1", target_id="npc1",
                          metadata={"pool": 10, "base_damage": 2})
    found = False
    for seed in range(100):
        result = rs.resolve_action(intent, state, rng=random.Random(seed))
        if result.outcome in {"success", "critical_success"}:
            assert any(m.kind == "damage" and m.resource == "Health"
                       for m in result.state_mutations)
            found = True
            break
    assert found


def test_three_successes_is_critical():
    rs = AlienRPGRuleset()
    state = make_state()
    intent = ActionIntent(action_type="skill_check", actor_id="pc1",
                          metadata={"pool": 12})
    found = False
    for seed in range(300):
        result = rs.resolve_action(intent, state, rng=random.Random(seed))
        if result.dice_rolled["successes"] >= 3:
            assert result.outcome == "critical_success"
            found = True
            break
    assert found


def test_move_no_check():
    rs = AlienRPGRuleset()
    state = make_state()
    intent = ActionIntent(action_type="move", actor_id="pc1", target_location_id="loc2")
    result = rs.resolve_action(intent, state)
    assert result.check_required is False
    assert any(m.kind == "move" for m in result.state_mutations)


def test_system_prompt_fragment():
    rs = AlienRPGRuleset()
    state = make_state()
    assert "Game Mother" in rs.system_prompt_fragment(state)
