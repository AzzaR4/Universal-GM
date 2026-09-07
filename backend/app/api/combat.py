"""Combat encounter endpoints: start, resolve an action, end, and fetch state.

Combat actions are resolved mechanically by the Rules Engine (no AI call), so the
turn-based tracker stays fully playable even without a configured AI provider.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.core.exceptions import NotFoundError
from app.game.rules.base_ruleset import ActionIntent
from app.game.rules.rules_engine import rules_engine
from app.game.state.game_state import DamageMutation
from app.game.state.state_manager import StateManager

router = APIRouter(prefix="/api/campaigns/{campaign_id}/combat", tags=["combat"])


class StartCombatRequest(BaseModel):
    enemy_ids: list[str] | None = None
    default_enemy_hp: int = 10


class CombatActionRequest(BaseModel):
    actor_id: str | None = None
    target_id: str | None = None
    action_type: str = "attack"
    skill_used: str | None = None
    description: str = ""
    raw_text: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    end_turn: bool = True


@router.get("")
async def get_combat(campaign_id: str, session: AsyncSession = Depends(db_session)) -> dict:
    manager = StateManager(session)
    combat = await manager.get_combat(campaign_id)
    return {"active": bool(combat and combat.active), "combat": combat.to_dict() if combat else None}


@router.post("/start")
async def start_combat(
    campaign_id: str,
    payload: StartCombatRequest,
    session: AsyncSession = Depends(db_session),
) -> dict:
    manager = StateManager(session)
    combat = await manager.start_combat(
        campaign_id, enemy_ids=payload.enemy_ids, default_enemy_hp=payload.default_enemy_hp
    )
    return {"active": combat.active, "combat": combat.to_dict()}


@router.post("/action")
async def combat_action(
    campaign_id: str,
    payload: CombatActionRequest,
    session: AsyncSession = Depends(db_session),
) -> dict:
    manager = StateManager(session)

    # Ensure a combat is running.
    existing = await manager.get_combat(campaign_id)
    if existing is None or not existing.active:
        raise NotFoundError("No active combat for this campaign.")

    # Resolve the action mechanically via the Rules Engine (no AI).
    state = await manager.load(campaign_id)
    intent = ActionIntent(
        action_type=payload.action_type,
        description=payload.description,
        actor_id=payload.actor_id,
        skill_used=payload.skill_used,
        target_id=payload.target_id,
        raw_text=payload.raw_text or payload.description,
        metadata=payload.metadata,
    )
    result = rules_engine.resolve(intent, state)

    # Sum any damage the ruleset assigned to the target.
    damage = sum(
        m.amount
        for m in result.state_mutations
        if isinstance(m, DamageMutation) and m.character_id == payload.target_id
    )

    combat = await manager.apply_combat_action(
        campaign_id,
        actor_id=payload.actor_id,
        target_id=payload.target_id,
        damage=int(damage),
        note=result.mechanical_description,
        end_turn=payload.end_turn,
    )
    return {
        "active": combat.active,
        "combat": combat.to_dict(),
        "result": {
            "outcome": result.outcome,
            "outcome_label": result.outcome_label,
            "dice": result.dice_rolled,
            "damage": int(damage),
            "mechanical_description": result.mechanical_description,
        },
    }


@router.post("/end")
async def end_combat(campaign_id: str, session: AsyncSession = Depends(db_session)) -> dict:
    manager = StateManager(session)
    await manager.end_combat(campaign_id)
    return {"active": False, "combat": None}
