"""Tests for session lifecycle and recap generation."""
from __future__ import annotations

import pytest

from app.api.campaigns import create_campaign
from app.api.schemas import CampaignCreate
from app.api.sessions_api import get_session, list_sessions, start_session
from app.db.models import EventLog, Session
from app.game.session_recap import (
    build_recap_prompt,
    compose_recap,
    compute_xp,
    count_player_actions,
    extract_key_events,
    fallback_recap,
)

pytestmark = pytest.mark.asyncio


class FakeProvider:
    """Streams a fixed 3-paragraph recap."""

    async def stream_text(self, system, user):
        for chunk in ["Para one. ", "Para two. ", "Para three."]:
            yield chunk


async def _campaign(session):
    return await create_campaign(
        CampaignCreate(name="Saga", description="a grand quest"), session=session
    )


async def _log(session, campaign_id, event_type="action", **data):
    session.add(EventLog(campaign_id=campaign_id, event_type=event_type, data=data))
    await session.commit()


async def test_start_session_sets_current(session):
    camp = await _campaign(session)
    s = await start_session(camp.id, session=session)
    assert s.campaign_id == camp.id
    assert s.ended_at is None
    await session.refresh(camp)
    assert camp.current_session_id == s.id


async def test_start_session_unknown_campaign(session):
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await start_session("nope", session=session)


async def test_list_sessions(session):
    camp = await _campaign(session)
    await start_session(camp.id, session=session)
    await start_session(camp.id, session=session)
    rows = await list_sessions(camp.id, session=session)
    assert len(rows) == 2


async def test_get_session_detail(session):
    camp = await _campaign(session)
    s = await start_session(camp.id, session=session)
    got = await get_session(camp.id, s.id, session=session)
    assert got.id == s.id


async def test_get_session_not_found(session):
    from fastapi import HTTPException

    camp = await _campaign(session)
    with pytest.raises(HTTPException):
        await get_session(camp.id, "missing", session=session)


def test_count_player_actions():
    events = [
        EventLog(campaign_id="c", event_type="action", data={}),
        EventLog(campaign_id="c", event_type="narration_generated", data={}),
        EventLog(campaign_id="c", event_type="action", data={}),
    ]
    assert count_player_actions(events) == 2


def test_compute_xp_rewards_criticals():
    events = [
        EventLog(campaign_id="c", event_type="action", data={"outcome": "success"}),
        EventLog(campaign_id="c", event_type="action", data={"outcome": "critical_success"}),
    ]
    # 2 actions * 10 + 1 crit * 25 = 45
    assert compute_xp(events) == 45


def test_extract_key_events_limits_and_filters():
    events = [
        EventLog(campaign_id="c", event_type="narration_generated", data={"summary": "A big fight"}),
        EventLog(campaign_id="c", event_type="misc", data={"summary": "ignored"}),
    ]
    key = extract_key_events(events)
    assert len(key) == 1
    assert key[0]["description"] == "A big fight"


def test_fallback_recap_has_three_paragraphs():
    from app.db.models import Campaign

    camp = Campaign(name="Test", description="a dark tale")
    events = [EventLog(campaign_id="c", event_type="action", data={"summary": "did a thing"})]
    key = extract_key_events(events)
    recap = fallback_recap(camp, events, key)
    assert recap.count("\n\n") == 2  # three paragraphs


def test_build_recap_prompt_includes_events():
    from app.db.models import Campaign

    camp = Campaign(name="Test", description="")
    events = [EventLog(campaign_id="c", event_type="action", data={"summary": "slew a beast"})]
    system, user = build_recap_prompt(camp, events)
    assert "3-paragraph" in system
    assert "slew a beast" in user


async def test_compose_recap_fallback(session):
    camp = await _campaign(session)
    s = await start_session(camp.id, session=session)
    await _log(session, camp.id, "action", summary="fought goblins", outcome="success")
    await _log(session, camp.id, "action", summary="found gold", outcome="critical_success")
    finalized = await compose_recap(session, camp.id, s.id, provider=None)
    assert finalized.summary
    assert finalized.ended_at is not None
    assert finalized.player_actions_count == 2
    assert finalized.xp_awarded == 2 * 10 + 1 * 25
    assert len(finalized.key_events) == 2
    await session.refresh(camp)
    assert camp.current_session_id is None


async def test_compose_recap_with_provider(session):
    camp = await _campaign(session)
    s = await start_session(camp.id, session=session)
    await _log(session, camp.id, "action", summary="an event")
    finalized = await compose_recap(session, camp.id, s.id, provider=FakeProvider())
    assert "Para one." in finalized.summary
    assert "Para three." in finalized.summary


async def test_compose_recap_empty_session(session):
    camp = await _campaign(session)
    s = await start_session(camp.id, session=session)
    finalized = await compose_recap(session, camp.id, s.id, provider=None)
    assert finalized.summary  # still produces a recap
    assert finalized.player_actions_count == 0
    assert finalized.xp_awarded == 0
