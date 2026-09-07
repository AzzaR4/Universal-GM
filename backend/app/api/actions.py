"""Player action pipeline endpoint. Returns a Server-Sent Events stream."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.deps import db_session
from app.api.schemas import ActionRequest
from app.db.base import SessionLocal
from app.game.narrative.narrative_engine import NarrativeEngine

router = APIRouter(prefix="/api/campaigns/{campaign_id}", tags=["actions"])


async def _event_generator(campaign_id: str, text: str):
    """Run the pipeline in its own session so the SSE stream owns its lifecycle."""
    async with SessionLocal() as session:
        engine = NarrativeEngine(session)
        try:
            async for event in engine.run_action(campaign_id, text):
                yield {"event": event["type"], "data": json.dumps(event["data"])}
        except Exception as exc:  # noqa: BLE001 - always terminate the stream cleanly
            yield {"event": "error", "data": json.dumps(str(exc))}


@router.post("/actions")
async def take_action(campaign_id: str, payload: ActionRequest) -> EventSourceResponse:
    return EventSourceResponse(_event_generator(campaign_id, payload.text))
