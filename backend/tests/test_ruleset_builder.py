"""Tests for the Ruleset Builder: custom ruleset CRUD, dynamic registration, export/import."""
from __future__ import annotations

import pytest

from app.api.rulesets_api import (
    create_custom_ruleset,
    delete_custom_ruleset,
    export_ruleset,
    get_custom_ruleset,
    import_ruleset,
    list_custom_rulesets,
    update_custom_ruleset,
)
from app.api.schemas import CustomRulesetCreate, CustomRulesetUpdate
from app.game.rules.base_ruleset import ActionIntent
from app.rulesets import registry
from app.rulesets.dynamic import DynamicRuleset

pytestmark = pytest.mark.asyncio


def _spec(name="mysystem", **kw):
    base = dict(
        name=name,
        display_name="My System",
        description="A test system",
        dice_formula="2d6",
        roll_mode="single",
        success_threshold=8,
        attributes=[{"name": "Grit", "label": "Grit", "min": 0, "max": 5, "default": 2}],
        resources=[{"name": "Health", "label": "Health", "min": 0, "max": 10, "color": "red"}],
        skills=[{"name": "Fighting", "label": "Fighting", "governing_attribute": "Grit"}],
        prompt_instructions="Be gritty.",
    )
    base.update(kw)
    return base


@pytest.fixture(autouse=True)
def _clean_registry():
    """Remove any custom rulesets registered during a test."""
    yield
    for rid in list(registry._REGISTRY.keys()):
        if not registry.is_builtin(rid):
            registry.unregister(rid)


# --------------------------- CRUD --------------------------- #
async def test_create_custom_ruleset(session):
    rs = await create_custom_ruleset(CustomRulesetCreate(**_spec()), session=session)
    assert rs.name == "mysystem"
    assert registry.is_registered("mysystem")


async def test_create_duplicate_name_conflict(session):
    from fastapi import HTTPException

    await create_custom_ruleset(CustomRulesetCreate(**_spec()), session=session)
    with pytest.raises(HTTPException):
        await create_custom_ruleset(CustomRulesetCreate(**_spec()), session=session)


async def test_create_invalid_name(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await create_custom_ruleset(
            CustomRulesetCreate(**_spec(name="Bad Name!")), session=session
        )


async def test_create_reserved_builtin_name(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await create_custom_ruleset(
            CustomRulesetCreate(**_spec(name="generic")), session=session
        )


async def test_list_custom_rulesets(session):
    await create_custom_ruleset(CustomRulesetCreate(**_spec(name="a")), session=session)
    await create_custom_ruleset(CustomRulesetCreate(**_spec(name="b")), session=session)
    rows = await list_custom_rulesets(session=session)
    assert len(rows) == 2


async def test_get_custom_ruleset_by_name(session):
    await create_custom_ruleset(CustomRulesetCreate(**_spec()), session=session)
    rs = await get_custom_ruleset("mysystem", session=session)
    assert rs.display_name == "My System"


async def test_update_custom_ruleset(session):
    await create_custom_ruleset(CustomRulesetCreate(**_spec()), session=session)
    updated = await update_custom_ruleset(
        "mysystem",
        CustomRulesetUpdate(success_threshold=10, display_name="Renamed"),
        session=session,
    )
    assert updated.success_threshold == 10
    assert updated.display_name == "Renamed"


async def test_delete_custom_ruleset(session):
    await create_custom_ruleset(CustomRulesetCreate(**_spec()), session=session)
    result = await delete_custom_ruleset("mysystem", session=session)
    assert result["deleted"] == "mysystem"
    assert not registry.is_registered("mysystem")


async def test_get_unknown_ruleset(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await get_custom_ruleset("ghost", session=session)


# --------------------------- Registration & resolution --------------------------- #
async def test_created_ruleset_usable_via_registry(session):
    await create_custom_ruleset(CustomRulesetCreate(**_spec()), session=session)
    rs = registry.get_ruleset("mysystem")
    data = rs.new_character_data(rs.default_config())
    assert data["attributes"]["Grit"] == 2
    assert data["resources"]["Health"]["max"] == 10
    assert "Fighting" in data["skills"]


async def test_load_custom_rulesets_from_db(session):
    await create_custom_ruleset(CustomRulesetCreate(**_spec(name="persisted")), session=session)
    registry.unregister("persisted")
    assert not registry.is_registered("persisted")
    count = await registry.load_custom_rulesets(session)
    assert count >= 1
    assert registry.is_registered("persisted")


def test_dynamic_single_roll_outcome():
    rs = DynamicRuleset(_spec(dice_formula="1d20", roll_mode="single", success_threshold=10))
    schema = rs.character_schema()
    assert schema["attributes"][0]["name"] == "Grit"


def test_dynamic_pool_count_successes():
    import random

    rs = DynamicRuleset(
        _spec(dice_formula="5d6", roll_mode="pool_count_successes", success_threshold=5)
    )
    from app.game.state.game_state import GameState

    state = GameState(
        campaign_id="c",
        campaign_name="Test",
        ruleset_id="mysystem",
        ruleset_config={},
        gm_config={},
        current_location_id=None,
    )
    intent = ActionIntent(action_type="skill_check", raw_text="try")
    result = rs.resolve_action(intent, state, rng=random.Random(1))
    assert "successes" in result.dice_rolled
    assert result.outcome in {
        "failure",
        "partial",
        "success",
        "critical_success",
    }


# --------------------------- Export / Import --------------------------- #
async def test_export_ruleset(session):
    await create_custom_ruleset(CustomRulesetCreate(**_spec()), session=session)
    export = await export_ruleset("mysystem", session=session)
    assert export["export_version"] == 1
    assert export["ruleset"]["name"] == "mysystem"
    assert export["ruleset"]["dice_formula"] == "2d6"


async def test_import_ruleset(session):
    export = {"ruleset": _spec(name="imported")}
    rs = await import_ruleset(export, session=session)
    assert rs.name == "imported"
    assert registry.is_registered("imported")


async def test_import_duplicate_suffixes_name(session):
    await create_custom_ruleset(CustomRulesetCreate(**_spec(name="dup")), session=session)
    rs = await import_ruleset({"ruleset": _spec(name="dup")}, session=session)
    assert rs.name == "dup-imported"


async def test_import_invalid_payload(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await import_ruleset({"bogus": True}, session=session)
