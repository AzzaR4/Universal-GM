"""Tests for the world simulation: faction CRUD, autonomy tick, world events."""
from __future__ import annotations

import pytest

from app.api.campaigns import create_campaign
from app.api.schemas import (
    CampaignCreate,
    FactionCreate,
    FactionUpdate,
    WorldEventCreate,
)
from app.api.world import (
    create_faction,
    create_world_event,
    delete_faction,
    list_factions,
    list_world_events,
    reveal_world_event,
    tick_world,
    update_faction,
)
from app.db.models import EventLog
from app.world.faction_engine import FactionEngine

pytestmark = pytest.mark.asyncio


async def _campaign(session):
    return await create_campaign(CampaignCreate(name="World"), session=session)


async def test_create_and_list_factions(session):
    camp = await _campaign(session)
    await create_faction(
        camp.id, FactionCreate(name="Red Hand", goals=["seize the pass"]), session=session
    )
    rows = await list_factions(camp.id, session=session)
    assert len(rows) == 1
    assert rows[0].name == "Red Hand"
    assert rows[0].resources == 50


async def test_create_faction_unknown_campaign(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await create_faction("nope", FactionCreate(name="X"), session=session)


async def test_update_faction(session):
    camp = await _campaign(session)
    f = await create_faction(camp.id, FactionCreate(name="Guild"), session=session)
    updated = await update_faction(
        camp.id,
        f.id,
        FactionUpdate(disposition="hostile", influence=80),
        session=session,
    )
    assert updated.disposition == "hostile"
    assert updated.influence == 80


async def test_update_faction_not_found(session):
    from fastapi import HTTPException

    camp = await _campaign(session)
    with pytest.raises(HTTPException):
        await update_faction(camp.id, "missing", FactionUpdate(name="Y"), session=session)


async def test_delete_faction(session):
    camp = await _campaign(session)
    f = await create_faction(camp.id, FactionCreate(name="Cult"), session=session)
    result = await delete_faction(camp.id, f.id, session=session)
    assert result["deleted"] == f.id
    assert await list_factions(camp.id, session=session) == []


async def test_manual_world_event(session):
    camp = await _campaign(session)
    ev = await create_world_event(
        camp.id,
        WorldEventCreate(title="A comet appears", description="Ill omen"),
        session=session,
    )
    assert ev.title == "A comet appears"
    events = await list_world_events(camp.id, session=session)
    assert len(events) == 1


async def test_reveal_world_event(session):
    camp = await _campaign(session)
    ev = await create_world_event(
        camp.id,
        WorldEventCreate(title="Hidden plot", is_revealed=False),
        session=session,
    )
    revealed = await reveal_world_event(camp.id, ev.id, is_revealed=True, session=session)
    assert revealed.is_revealed is True


async def test_list_world_events_filter_revealed(session):
    camp = await _campaign(session)
    await create_world_event(
        camp.id, WorldEventCreate(title="Seen", is_revealed=True), session=session
    )
    await create_world_event(
        camp.id, WorldEventCreate(title="Unseen", is_revealed=False), session=session
    )
    revealed = await list_world_events(camp.id, revealed=True, session=session)
    hidden = await list_world_events(camp.id, revealed=False, session=session)
    assert len(revealed) == 1 and revealed[0].title == "Seen"
    assert len(hidden) == 1 and hidden[0].title == "Unseen"


async def test_tick_force_creates_events(session):
    camp = await _campaign(session)
    await create_faction(
        camp.id,
        FactionCreate(name="Aggressors", autonomy_level="aggressive", disposition="hostile"),
        session=session,
    )
    events = await tick_world(camp.id, force=True, session=session)
    assert len(events) == 1
    assert events[0].faction_id is not None
    assert events[0].description  # deterministic fallback produced prose


async def test_tick_skips_passive_factions(session):
    camp = await _campaign(session)
    await create_faction(
        camp.id, FactionCreate(name="Sleepers", autonomy_level="passive"), session=session
    )
    events = await tick_world(camp.id, force=True, session=session)
    assert events == []


async def test_tick_respects_threshold(session):
    camp = await _campaign(session)
    await create_faction(
        camp.id, FactionCreate(name="Watchers", autonomy_level="active"), session=session
    )
    # No player actions logged yet -> below the active threshold of 5.
    engine = FactionEngine(session)
    events = await engine.tick(camp.id, force=False)
    assert events == []


async def test_tick_acts_after_threshold_actions(session):
    camp = await _campaign(session)
    await create_faction(
        camp.id, FactionCreate(name="Movers", autonomy_level="aggressive"), session=session
    )
    # Aggressive threshold is 2 player actions.
    for _ in range(2):
        session.add(EventLog(campaign_id=camp.id, event_type="action", data={}))
    await session.commit()
    engine = FactionEngine(session)
    events = await engine.tick(camp.id, force=False)
    assert len(events) == 1


async def test_tick_applies_impact_to_faction(session):
    camp = await _campaign(session)
    f = await create_faction(
        camp.id,
        FactionCreate(name="Barons", autonomy_level="aggressive", disposition="hostile"),
        session=session,
    )
    before_influence = f.influence
    await tick_world(camp.id, force=True, session=session)
    await session.refresh(f)
    # Hostile fallback grants +8 influence.
    assert f.influence == before_influence + 8
    assert f.last_acted_at is not None


async def test_faction_prompt_contains_goals(session):
    camp = await _campaign(session)
    f = await create_faction(
        camp.id, FactionCreate(name="Seers", goals=["find the relic"]), session=session
    )
    engine = FactionEngine(session)
    system, user = engine.build_faction_prompt(f)
    assert "Seers" in user
    assert "find the relic" in user
    assert "JSON" in system


async def test_impact_clamped_to_bounds(session):
    camp = await _campaign(session)
    f = await create_faction(
        camp.id,
        FactionCreate(name="Maxed", influence=98, autonomy_level="aggressive", disposition="hostile"),
        session=session,
    )
    await tick_world(camp.id, force=True, session=session)
    await session.refresh(f)
    assert f.influence <= 100
