"""Auxiliary SSE endpoint: replays recent campaign events for reconnecting UIs."""
from __future__ import annotations

import json

from fastapi import APIRouter
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.db.base import SessionLocal
from app.db.models import EventLog

router = APIRouter(prefix="/api/campaigns/{campaign_id}", tags=["stream"])


async def _replay(campaign_id: str, limit: int):
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(EventLog)
                .where(EventLog.campaign_id == campaign_id)
                .order_by(EventLog.timestamp.desc())
                .limit(limit)
            )
        ).scalars().all()
        for row in reversed(rows):
            yield {
                "event": row.event_type,
                "data": json.dumps({"id": row.id, "data": row.data}),
            }
        yield {"event": "complete", "data": json.dumps({"replayed": len(rows)})}


@router.get("/stream")
async def stream_recent(campaign_id: str, limit: int = 20) -> EventSourceResponse:
    return EventSourceResponse(_replay(campaign_id, limit))
