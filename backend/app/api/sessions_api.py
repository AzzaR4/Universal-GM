"""Session lifecycle API: list, start, end (SSE recap), detail."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import db_session
from app.api.schemas import SessionOut
from app.db.base import SessionLocal
from app.db.models import Campaign, Session
from app.game.session_recap import (
    build_recap_prompt,
    collect_session_events,
    fallback_recap,
    finalize_session,
)

router = APIRouter(prefix="/api/campaigns/{campaign_id}/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
async def list_sessions(
    campaign_id: str, session: AsyncSession = Depends(db_session)
) -> list[Session]:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    rows = (
        await session.execute(
            select(Session)
            .where(Session.campaign_id == campaign_id)
            .order_by(Session.started_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.post("/start", response_model=SessionOut)
async def start_session(
    campaign_id: str, session: AsyncSession = Depends(db_session)
) -> Session:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    game_session = Session(campaign_id=campaign_id)
    session.add(game_session)
    await session.commit()
    await session.refresh(game_session)
    campaign.current_session_id = game_session.id
    await session.commit()
    await session.refresh(game_session)
    return game_session


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    campaign_id: str, session_id: str, session: AsyncSession = Depends(db_session)
) -> Session:
    game_session = await session.get(Session, session_id)
    if game_session is None or game_session.campaign_id != campaign_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return game_session


@router.post("/{session_id}/end")
async def end_session(campaign_id: str, session_id: str) -> EventSourceResponse:
    """End a session and stream the AI-generated recap over SSE.

    Uses its own DB session (SessionLocal) because the response outlives the
    request-scoped dependency session.
    """

    async def _stream():
        async with SessionLocal() as session:
            campaign = await session.get(Campaign, campaign_id)
            game_session = await session.get(Session, session_id)
            if campaign is None or game_session is None:
                yield {"event": "error", "data": json.dumps({"detail": "Not found"})}
                return

            events = await collect_session_events(
                session, campaign_id, game_session.started_at
            )

            # Try streaming from the active AI provider; degrade gracefully.
            summary = ""
            provider = None
            try:
                from app.ai.provider_registry import get_active_provider

                provider = await get_active_provider(session)
            except Exception:  # noqa: BLE001
                provider = None

            if provider is not None:
                system, user = build_recap_prompt(campaign, events)
                try:
                    async for chunk in provider.stream_text(system, user):
                        summary += chunk
                        yield {"event": "recap", "data": json.dumps({"text": chunk})}
                except Exception:  # noqa: BLE001
                    summary = ""

            if not summary.strip():
                from app.game.session_recap import extract_key_events

                summary = fallback_recap(
                    campaign, events, extract_key_events(events)
                )
                yield {"event": "recap", "data": json.dumps({"text": summary})}

            finalized = await finalize_session(
                session, campaign, game_session, events, summary
            )
            yield {
                "event": "complete",
                "data": json.dumps(
                    {
                        "session_id": finalized.id,
                        "xp_awarded": finalized.xp_awarded,
                        "key_events": finalized.key_events,
                        "player_actions_count": finalized.player_actions_count,
                    }
                ),
            }

    return EventSourceResponse(_stream())
