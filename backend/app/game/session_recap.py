"""Session recap generation helpers (pure / reusable by API + SSE endpoint)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Campaign, EventLog, Session

# XP awarded per player action when a ruleset doesn't override the rule.
XP_PER_ACTION = 10
XP_PER_CRITICAL = 25


def _text_of(event: EventLog) -> str:
    data = event.data or {}
    return str(
        data.get("summary")
        or data.get("narration")
        or data.get("description")
        or ""
    ).strip()


async def collect_session_events(
    session: AsyncSession, campaign_id: str, since: datetime | None
) -> list[EventLog]:
    stmt = select(EventLog).where(EventLog.campaign_id == campaign_id)
    if since is not None:
        stmt = stmt.where(EventLog.timestamp >= since)
    stmt = stmt.order_by(EventLog.timestamp.asc())
    return list((await session.execute(stmt)).scalars().all())


def extract_key_events(events: list[EventLog]) -> list[dict]:
    key: list[dict] = []
    for e in events:
        if e.event_type not in {"narration_generated", "action", "combat", "world_change"}:
            continue
        text = _text_of(e)
        if not text:
            continue
        key.append(
            {
                "timestamp": (e.timestamp or datetime.now(timezone.utc)).isoformat(),
                "description": text[:200],
            }
        )
    return key[:12]


def count_player_actions(events: list[EventLog]) -> int:
    return sum(1 for e in events if e.event_type == "action")


def compute_xp(events: list[EventLog]) -> int:
    actions = count_player_actions(events)
    crits = 0
    for e in events:
        data = e.data or {}
        if data.get("outcome") in {"critical_success", "critical_failure"}:
            crits += 1
    return actions * XP_PER_ACTION + crits * XP_PER_CRITICAL


def build_recap_prompt(campaign: Campaign, events: list[EventLog]) -> tuple[str, str]:
    system = (
        "You are the Game Master writing a session recap for a tabletop RPG. "
        "Summarize the session as a vivid, engaging 3-paragraph recap: paragraph 1 "
        "sets the scene and what the party set out to do, paragraph 2 covers the key "
        "events and turning points, and paragraph 3 ends on the current cliffhanger "
        "or open threads. Write in past tense, second-person plural ('you')."
    )
    lines = [f"Campaign: {campaign.name}"]
    if campaign.description:
        lines.append(f"Premise: {campaign.description}")
    lines.append("\nEvents this session (chronological):")
    any_event = False
    for e in events:
        text = _text_of(e)
        if text:
            lines.append(f"- {text}")
            any_event = True
    if not any_event:
        lines.append("- (a quiet session with little of note)")
    lines.append("\nWrite the 3-paragraph recap now.")
    return system, "\n".join(lines)


def fallback_recap(campaign: Campaign, events: list[EventLog], key_events: list[dict]) -> str:
    """Deterministic recap used when no AI provider is configured."""
    actions = count_player_actions(events)
    intro = (
        f"In this session of {campaign.name}, the party pressed onward through "
        f"their adventure. "
    )
    if campaign.description:
        intro += f"The tale of {campaign.description} continued to unfold."
    if key_events:
        middle = "Key moments included: " + "; ".join(
            k["description"] for k in key_events[:5]
        ) + "."
    else:
        middle = (
            "The party spent the session in quieter pursuits, with no single moment "
            "rising above the rest."
        )
    outro = (
        f"By the end of the session the party had taken {actions} notable "
        "action(s), and new threads were left dangling — ready to be picked up when "
        "the story resumes. (AI narration unavailable — configure an AI provider in "
        "Settings for a richer recap.)"
    )
    return f"{intro}\n\n{middle}\n\n{outro}"


async def finalize_session(
    session: AsyncSession,
    campaign: Campaign,
    game_session: Session,
    events: list[EventLog],
    summary: str,
) -> Session:
    key_events = extract_key_events(events)
    game_session.summary = summary
    game_session.key_events = key_events
    game_session.player_actions_count = count_player_actions(events)
    game_session.xp_awarded = compute_xp(events)
    game_session.ended_at = datetime.now(timezone.utc)
    if campaign.current_session_id == game_session.id:
        campaign.current_session_id = None
    await session.commit()
    await session.refresh(game_session)
    return game_session


async def compose_recap(
    session: AsyncSession,
    campaign_id: str,
    session_id: str,
    provider=None,
) -> Session:
    """Generate and persist a recap for a session (non-streaming, testable)."""
    campaign = await session.get(Campaign, campaign_id)
    game_session = await session.get(Session, session_id)
    events = await collect_session_events(
        session, campaign_id, game_session.started_at if game_session else None
    )
    key_events = extract_key_events(events)

    summary = ""
    if provider is not None:
        system, user = build_recap_prompt(campaign, events)
        try:
            async for chunk in provider.stream_text(system, user):
                summary += chunk
        except Exception:  # noqa: BLE001
            summary = ""
    if not summary.strip():
        summary = fallback_recap(campaign, events, key_events)

    return await finalize_session(session, campaign, game_session, events, summary)
