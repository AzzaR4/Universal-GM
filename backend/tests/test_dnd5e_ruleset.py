"""Tests for the D&D 5e-style (d20) ruleset."""
from __future__ import annotations

import random

import pytest

from app.core.exceptions import RuleViolationError
from app.game.rules.base_ruleset import ActionIntent
from app.game.state.game_state import CharacterView, GameState, LocationView, NPCView
from app.rulesets.dnd5e.ruleset import DnD5eRuleset
from app.rulesets.dnd5e.schema import ability_modifier, proficiency_bonus_for_level


def make_state(pc_data: dict | None = None) -> GameState:
    rs = DnD5eRuleset()
    data = pc_data or rs.new_character_data({})
    pc = CharacterView(
        id="pc1",
        name="Aragorn",
        description="A ranger",
        is_player_character=True,
        ruleset_data=data,
        conditions=[],
        inventory=[],
        location_id="loc1",
        status="alive",
    )
    npc = NPCView(
        id="npc1", name="Orc", description="A brutish orc",
        location_id="loc1", current_activity="snarling", status="alive",
    )
    loc = LocationView(id="loc1", name="Pass", description="cold", atmosphere="bleak")
    loc2 = LocationView(id="loc2", name="Wood", description="green", atmosphere="quiet")
    return GameState(
        campaign_id="c1", campaign_name="T", ruleset_id="dnd5e",
        ruleset_config=rs.default_config(), gm_config={}, current_location_id="loc1",
        characters=[pc], npcs=[npc], locations=[loc, loc2],
    )


def test_ability_modifier_math():
    assert ability_modifier(10) == 0
    assert ability_modifier(12) == 1
    assert ability_modifier(8) == -1
    assert ability_modifier(20) == 5
    assert ability_modifier(1) == -5


def test_proficiency_progression():
    assert proficiency_bonus_for_level(1) == 2
    assert proficiency_bonus_for_level(4) == 2
    assert proficiency_bonus_for_level(5) == 3
    assert proficiency_bonus_for_level(17) == 6


def test_default_config_and_new_character():
    rs = DnD5eRuleset()
    cfg = rs.default_config()
    assert cfg["crit_on"] == 20 and cfg["fumble_on"] == 1
    data = rs.new_character_data(cfg)
    assert set(data["abilities"].keys()) == {"str", "dex", "con", "int", "wis", "cha"}
    assert data["resources"]["HP"]["current"] > 0
    assert data["proficiency_bonus"] == 2


def test_character_schema_has_abilities_and_skills():
    rs = DnD5eRuleset()
    schema = rs.character_schema()
    assert len(schema["abilities"]) == 6
    assert any(s["name"] == "Stealth" for s in schema["skills"])


def test_validate_dead_actor():
    rs = DnD5eRuleset()
    state = make_state()
    state.characters[0].status = "defeated"
    intent = ActionIntent(action_type="attack", actor_id="pc1", target_id="npc1")
    with pytest.raises(RuleViolationError):
        rs.validate_action(intent, state)


def test_attack_produces_d20_roll():
    rs = DnD5eRuleset()
    state = make_state()
    intent = ActionIntent(action_type="attack", actor_id="pc1", target_id="npc1",
                          metadata={"damage_dice": "1d8", "target_ac": 10})
    result = rs.resolve_action(intent, state, rng=random.Random(3))
    assert result.check_required is True
    assert result.dice_rolled["sides"] == 20
    assert result.outcome in {"critical_success", "success", "failure", "critical_failure"}


def test_attack_crit_and_fumble_exist_across_seeds():
    rs = DnD5eRuleset()
    state = make_state()
    intent = ActionIntent(action_type="attack", actor_id="pc1", target_id="npc1",
                          metadata={"target_ac": 12})
    outcomes = set()
    crit_damage_seen = False
    for seed in range(200):
        result = rs.resolve_action(intent, state, rng=random.Random(seed))
        outcomes.add(result.outcome)
        if result.outcome == "critical_success":
            # A critical hit must generate a damage mutation.
            assert any(m.kind == "damage" for m in result.state_mutations)
            crit_damage_seen = True
    assert "critical_success" in outcomes
    assert "critical_failure" in outcomes
    assert crit_damage_seen


def test_skill_check_proficiency_increases_total():
    rs = DnD5eRuleset()
    data = rs.new_character_data({})
    data["abilities"]["dex"] = 10  # modifier 0 to isolate proficiency
    # Not proficient.
    state = make_state(pc_data={**data, "proficient_skills": []})
    intent = ActionIntent(action_type="skill_check", actor_id="pc1", skill_used="Stealth",
                          metadata={"dc": 10})
    r1 = rs.resolve_action(intent, state, rng=random.Random(7))
    # Proficient.
    state2 = make_state(pc_data={**data, "proficient_skills": ["Stealth"]})
    r2 = rs.resolve_action(intent, state2, rng=random.Random(7))
    assert r2.dice_rolled["modifier"] > r1.dice_rolled["modifier"]


def test_saving_throw_resolves():
    rs = DnD5eRuleset()
    state = make_state()
    intent = ActionIntent(action_type="saving_throw", actor_id="pc1",
                          metadata={"ability": "con", "dc": 12})
    result = rs.resolve_action(intent, state, rng=random.Random(1))
    assert result.check_required is True
    assert "saving throw" in result.mechanical_description.lower()


def test_move_no_check():
    rs = DnD5eRuleset()
    state = make_state()
    intent = ActionIntent(action_type="move", actor_id="pc1", target_location_id="loc2")
    result = rs.resolve_action(intent, state)
    assert result.check_required is False
    assert any(m.kind == "move" for m in result.state_mutations)


def test_initiative_uses_dex():
    rs = DnD5eRuleset()
    data = rs.new_character_data({})
    data["abilities"]["dex"] = 16  # +3
    assert rs.get_initiative(data) == 13


def test_system_prompt_fragment():
    rs = DnD5eRuleset()
    state = make_state()
    assert "d20" in rs.system_prompt_fragment(state)
