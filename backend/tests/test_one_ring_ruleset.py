"""Tests for The One Ring-style ruleset (feat die + success dice)."""
from __future__ import annotations

import random

import pytest

from app.core.exceptions import RuleViolationError
from app.game.rules.base_ruleset import ActionIntent
from app.game.state.game_state import CharacterView, GameState, LocationView, NPCView
from app.rulesets.one_ring.ruleset import OneRingRuleset
from app.rulesets.one_ring.schema import FEAT_GREAT, FEAT_ILL_OMEN


def make_state(conditions=None, pc_data=None) -> GameState:
    rs = OneRingRuleset()
    data = pc_data or rs.new_character_data({})
    pc = CharacterView(
        id="pc1", name="Beren", description="A wanderer", is_player_character=True,
        ruleset_data=data, conditions=conditions or [], inventory=[],
        location_id="loc1", status="alive",
    )
    npc = NPCView(id="npc1", name="Warg", description="A wolf",
                  location_id="loc1", current_activity="prowling", status="alive")
    loc = LocationView(id="loc1", name="Moor", description="wide", atmosphere="lonely")
    loc2 = LocationView(id="loc2", name="Hill", description="high", atmosphere="windy")
    return GameState(
        campaign_id="c1", campaign_name="T", ruleset_id="one_ring",
        ruleset_config=rs.default_config(), gm_config={}, current_location_id="loc1",
        characters=[pc], npcs=[npc], locations=[loc, loc2],
    )


def test_default_config_and_character():
    rs = OneRingRuleset()
    cfg = rs.default_config()
    assert cfg["default_tn"] == 14
    data = rs.new_character_data(cfg)
    assert "Endurance" in data["resources"]
    assert "Hope" in data["resources"]
    assert "Shadow" in data["resources"]


def test_character_schema_has_conditions():
    rs = OneRingRuleset()
    schema = rs.character_schema()
    names = {c["name"] for c in schema["conditions"]}
    assert "Weary" in names and "Miserable" in names


def test_validate_dead_actor():
    rs = OneRingRuleset()
    state = make_state()
    state.characters[0].status = "defeated"
    intent = ActionIntent(action_type="skill_check", actor_id="pc1")
    with pytest.raises(RuleViolationError):
        rs.validate_action(intent, state)


def test_roll_structure_has_feat_and_success_dice():
    rs = OneRingRuleset()
    state = make_state()
    intent = ActionIntent(action_type="skill_check", actor_id="pc1", skill_used="Travel",
                          metadata={"skill_rank": 3})
    result = rs.resolve_action(intent, state, rng=random.Random(2))
    d = result.dice_rolled
    assert "feat_die" in d
    assert len(d["success_dice"]) == 3


def test_feat_die_12_is_auto_success():
    rs = OneRingRuleset()
    state = make_state()
    intent = ActionIntent(action_type="skill_check", actor_id="pc1",
                          metadata={"skill_rank": 1, "tn": 99})  # impossible TN
    # Find a seed where the feat die rolls 12 -> should still succeed.
    found = False
    for seed in range(500):
        result = rs.resolve_action(intent, state, rng=random.Random(seed))
        if result.dice_rolled["feat_die"] == FEAT_GREAT:
            assert result.outcome in {"success", "critical_success"}
            found = True
            break
    assert found


def test_ill_omen_while_miserable_is_critical_failure():
    rs = OneRingRuleset()
    state = make_state(conditions=["Miserable"])
    intent = ActionIntent(action_type="skill_check", actor_id="pc1",
                          metadata={"skill_rank": 2, "tn": 5})
    found = False
    for seed in range(500):
        result = rs.resolve_action(intent, state, rng=random.Random(seed))
        if result.dice_rolled["feat_die"] == FEAT_ILL_OMEN:
            assert result.outcome == "critical_failure"
            found = True
            break
    assert found


def test_weary_reduces_low_success_dice():
    rs = OneRingRuleset()
    # Weary should never score more than a non-weary roll on the same seed.
    intent = ActionIntent(action_type="skill_check", actor_id="pc1",
                          metadata={"skill_rank": 4, "tn": 14})
    for seed in range(50):
        normal = rs.resolve_action(intent, make_state(), rng=random.Random(seed))
        weary = rs.resolve_action(
            intent, make_state(conditions=["Weary"]), rng=random.Random(seed)
        )
        assert weary.dice_rolled["total"] <= normal.dice_rolled["total"]


def test_two_sixes_yields_great_success():
    rs = OneRingRuleset()
    state = make_state()
    intent = ActionIntent(action_type="skill_check", actor_id="pc1",
                          metadata={"skill_rank": 6, "tn": 1})
    found = False
    for seed in range(500):
        result = rs.resolve_action(intent, state, rng=random.Random(seed))
        if result.dice_rolled["sixes"] >= 2 and result.dice_rolled["total"] >= 1:
            assert result.outcome == "critical_success"
            found = True
            break
    assert found


def test_attack_damage_on_success():
    rs = OneRingRuleset()
    state = make_state()
    intent = ActionIntent(action_type="attack", actor_id="pc1", target_id="npc1",
                          metadata={"skill_rank": 6, "tn": 1, "damage_dice": "1d6"})
    found = False
    for seed in range(200):
        result = rs.resolve_action(intent, state, rng=random.Random(seed))
        if result.outcome in {"success", "critical_success"}:
            assert any(m.kind == "damage" and m.resource == "Endurance"
                       for m in result.state_mutations)
            found = True
            break
    assert found


def test_move_no_check():
    rs = OneRingRuleset()
    state = make_state()
    intent = ActionIntent(action_type="move", actor_id="pc1", target_location_id="loc2")
    result = rs.resolve_action(intent, state)
    assert result.check_required is False
    assert any(m.kind == "move" for m in result.state_mutations)


def test_system_prompt_fragment():
    rs = OneRingRuleset()
    state = make_state()
    prompt = rs.system_prompt_fragment(state)
    assert "Loremaster" in prompt
