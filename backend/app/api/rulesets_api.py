"""Ruleset Builder API: CRUD for DB-stored custom rulesets + export/import.

Custom rulesets are registered into the live registry immediately on create /
update (and unregistered on delete) so they are usable without a restart.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.api.schemas import (
    CustomRulesetCreate,
    CustomRulesetOut,
    CustomRulesetUpdate,
)
from app.db.models import CustomRuleset
from app.rulesets import registry

router = APIRouter(prefix="/api/rulesets", tags=["rulesets"])

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _validate_name(name: str) -> None:
    if not _NAME_RE.match(name or ""):
        raise HTTPException(
            status_code=422,
            detail="Ruleset name must be lowercase alphanumeric (dashes/underscores allowed).",
        )
    if registry.is_builtin(name):
        raise HTTPException(status_code=409, detail="That name is reserved by a built-in ruleset.")


@router.get("/custom", response_model=list[CustomRulesetOut])
async def list_custom_rulesets(
    session: AsyncSession = Depends(db_session),
) -> list[CustomRuleset]:
    rows = (
        await session.execute(
            select(CustomRuleset).order_by(CustomRuleset.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.post("", response_model=CustomRulesetOut)
async def create_custom_ruleset(
    payload: CustomRulesetCreate, session: AsyncSession = Depends(db_session)
) -> CustomRuleset:
    _validate_name(payload.name)
    existing = (
        await session.execute(
            select(CustomRuleset).where(CustomRuleset.name == payload.name)
        )
    ).scalars().first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="A ruleset with that name already exists.")

    ruleset = CustomRuleset(**payload.model_dump())
    session.add(ruleset)
    await session.commit()
    await session.refresh(ruleset)
    # Register into the live registry immediately.
    registry.register_custom(ruleset)
    return ruleset


@router.get("/{ruleset_id}", response_model=CustomRulesetOut)
async def get_custom_ruleset(
    ruleset_id: str, session: AsyncSession = Depends(db_session)
) -> CustomRuleset:
    ruleset = await _get_by_id_or_name(session, ruleset_id)
    return ruleset


@router.patch("/{ruleset_id}", response_model=CustomRulesetOut)
async def update_custom_ruleset(
    ruleset_id: str,
    payload: CustomRulesetUpdate,
    session: AsyncSession = Depends(db_session),
) -> CustomRuleset:
    ruleset = await _get_by_id_or_name(session, ruleset_id)
    old_name = ruleset.name
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != old_name:
        _validate_name(data["name"])
    for field, value in data.items():
        setattr(ruleset, field, value)
    await session.commit()
    await session.refresh(ruleset)
    # Re-register (drop the old id if the name changed).
    if ruleset.name != old_name:
        registry.unregister(old_name)
    registry.register_custom(ruleset)
    return ruleset


@router.delete("/{ruleset_id}")
async def delete_custom_ruleset(
    ruleset_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    ruleset = await _get_by_id_or_name(session, ruleset_id)
    name = ruleset.name
    await session.delete(ruleset)
    await session.commit()
    registry.unregister(name)
    return {"deleted": ruleset_id}


@router.get("/{ruleset_id}/export")
async def export_ruleset(
    ruleset_id: str, session: AsyncSession = Depends(db_session)
) -> dict:
    ruleset = await _get_by_id_or_name(session, ruleset_id)
    return {
        "export_version": 1,
        "ruleset": {
            "name": ruleset.name,
            "display_name": ruleset.display_name,
            "description": ruleset.description,
            "dice_formula": ruleset.dice_formula,
            "roll_mode": ruleset.roll_mode,
            "success_threshold": ruleset.success_threshold,
            "attributes": ruleset.attributes,
            "resources": ruleset.resources,
            "skills": ruleset.skills,
            "prompt_instructions": ruleset.prompt_instructions,
        },
    }


@router.post("/import", response_model=CustomRulesetOut)
async def import_ruleset(
    payload: dict, session: AsyncSession = Depends(db_session)
) -> CustomRuleset:
    data = payload.get("ruleset") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or not data.get("name"):
        raise HTTPException(status_code=422, detail="Invalid ruleset file: missing 'ruleset.name'.")

    name = data["name"]
    # Avoid collisions by suffixing an imported duplicate.
    existing = (
        await session.execute(select(CustomRuleset).where(CustomRuleset.name == name))
    ).scalars().first()
    if existing is not None or registry.is_builtin(name):
        name = f"{name}-imported"
    data = {**data, "name": name}

    create = CustomRulesetCreate(**{k: v for k, v in data.items() if k in CustomRulesetCreate.model_fields})
    return await create_custom_ruleset(create, session=session)


async def _get_by_id_or_name(session: AsyncSession, ruleset_id: str) -> CustomRuleset:
    ruleset = await session.get(CustomRuleset, ruleset_id)
    if ruleset is None:
        ruleset = (
            await session.execute(
                select(CustomRuleset).where(CustomRuleset.name == ruleset_id)
            )
        ).scalars().first()
    if ruleset is None:
        raise HTTPException(status_code=404, detail="Custom ruleset not found")
    return ruleset
