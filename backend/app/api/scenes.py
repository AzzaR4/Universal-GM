"""Scene management endpoints.

A "scene" is a framed moment at a location: starting one sets the party's current
location, places the chosen NPCs there, and streams an opening narration. Ending a
scene records a memory so later narration can recall what happened.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.ai.provider_registry import get_active_provider
from app.api.deps import db_session
from app.core.exceptions import AIProviderError, NotFoundError
from app.db.base import SessionLocal
from app.db.models import Campaign, Location, NPC
from app.game.memory.memory_manager import MemoryManager
from app.game.narrative.narrator import Narrator
from app.game.rules.rules_engine import rules_engine
from app.game.state.state_manager import StateManager

router = APIRouter(prefix="/api/campaigns/{campaign_id}/scenes", tags=["scenes"])


class StartSceneRequest(BaseModel):
    location_id: str
    npc_ids: list[str] = Field(default_factory=list)
    prompt: str = ""


class EndSceneRequest(BaseModel):
    summary: str = ""


def _build_scene_prompt(state, location, npcs, extra: str) -> tuple[str, str]:
    system = rules_engine.system_prompt_fragment(state)
    parts: list[str] = ["=== SCENE FRAMING ==="]
    if location:
        parts.append(f"Location: {location.name}")
        if location.description:
            parts.append(f"Description: {location.description}")
        if location.atmosphere:
            parts.append(f"Atmosphere: {location.atmosphere}")
    if npcs:
        parts.append("\nNPCs present:")
        for n in npcs:
            activity = f" — {n.current_activity}" if n.current_activity else ""
            parts.append(f"- {n.name}: {n.description}{activity}")
    pc = state.get_player_character()
    if pc:
        parts.append(f"\nPlayer character: {pc.name} — {pc.description}")
    if extra:
        parts.append(f"\nScene direction: {extra}")
    parts.append(
        "\nNarrate an evocative opening for this scene that sets the mood, establishes the "
        "location, and introduces any NPCs present. End at a beat that invites the player to act."
    )
    return system, "\n".join(parts)


async def _scene_stream(campaign_id: str, payload: StartSceneRequest):
    async with SessionLocal() as session:
        manager = StateManager(session)
        # Apply scene setup: set current location and place NPCs.
        campaign = await session.get(Campaign, campaign_id)
        if campaign is None:
            yield {"event": "error", "data": json.dumps("Campaign not found")}
            return
        location = await session.get(Location, payload.location_id)
        if location is None:
            yield {"event": "error", "data": json.dumps("Location not found")}
            return
        campaign.current_location_id = payload.location_id
        for npc_id in payload.npc_ids:
            npc = await session.get(NPC, npc_id)
            if npc is not None:
                npc.location_id = payload.location_id
        await session.commit()

        yield {
            "event": "scene",
            "data": json.dumps({"location_id": payload.location_id, "npc_ids": payload.npc_ids}),
        }

        state = await manager.load(campaign_id)
        npcs_here = state.npcs_in_location(payload.location_id)
        loc_view = state.get_location(payload.location_id)
        system, user = _build_scene_prompt(state, loc_view, npcs_here, payload.prompt)

        provider = None
        try:
            provider = await get_active_provider(session)
        except AIProviderError:
            provider = None

        full_text = ""
        if provider is not None:
            narrator = Narrator(provider)
            try:
                async for chunk in narrator.narrate(system, user):
                    full_text += chunk
                    yield {"event": "narrative", "data": json.dumps(chunk)}
            except AIProviderError as exc:
                full_text = _fallback_scene(loc_view, str(exc))
                yield {"event": "narrative", "data": json.dumps(full_text)}
        else:
            full_text = _fallback_scene(loc_view, None)
            yield {"event": "narrative", "data": json.dumps(full_text)}

        # Record the scene opening as a memory.
        memory = MemoryManager(session)
        await memory.record(
            campaign_id,
            f"Scene at {loc_view.name if loc_view else 'a location'}: {full_text[:200]}",
            memory_type="scene",
            importance=0.6,
        )
        await session.commit()
        yield {"event": "complete", "data": json.dumps({"narration": full_text})}


def _fallback_scene(location, error: str | None) -> str:
    name = location.name if location else "this place"
    desc = location.description if location and location.description else ""
    note = (
        " (AI narration unavailable — configure an AI provider in Settings for full "
        "scene-setting.)"
    )
    return f"The scene opens at {name}. {desc}{note}"


@router.post("/start")
async def start_scene(campaign_id: str, payload: StartSceneRequest) -> EventSourceResponse:
    return EventSourceResponse(_scene_stream(campaign_id, payload))


@router.get("/current")
async def current_scene(campaign_id: str, session: AsyncSession = Depends(db_session)) -> dict:
    manager = StateManager(session)
    state = await manager.load(campaign_id)
    loc = state.get_location(state.current_location_id)
    npcs = state.npcs_in_location(state.current_location_id)
    return {
        "location": (
            {"id": loc.id, "name": loc.name, "description": loc.description, "atmosphere": loc.atmosphere}
            if loc
            else None
        ),
        "npcs": [{"id": n.id, "name": n.name, "current_activity": n.current_activity} for n in npcs],
    }


@router.post("/end")
async def end_scene(
    campaign_id: str, payload: EndSceneRequest, session: AsyncSession = Depends(db_session)
) -> dict:
    manager = StateManager(session)
    state = await manager.load(campaign_id)
    loc = state.get_location(state.current_location_id)
    summary = payload.summary or (
        f"The scene at {loc.name} concludes." if loc else "The scene concludes."
    )
    memory = MemoryManager(session)
    mem = await memory.record(campaign_id, summary, memory_type="scene_summary", importance=0.7)
    await session.commit()
    return {"recorded": True, "summary": summary, "memory_id": getattr(mem, "id", None)}
