"""Ruleset registry with auto-registration.

New rulesets register themselves here. The API exposes the list so the UI can
present available systems. Only the Generic ruleset is fully implemented in the
first vertical slice; placeholders advertise future systems.
"""
from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.game.rules.base_ruleset import BaseRuleset
from app.rulesets.alien_rpg.ruleset import AlienRPGRuleset
from app.rulesets.dnd5e.ruleset import DnD5eRuleset
from app.rulesets.generic.ruleset import GenericRuleset
from app.rulesets.one_ring.ruleset import OneRingRuleset

_REGISTRY: dict[str, BaseRuleset] = {}


# IDs of the built-in rulesets — these can never be overwritten or removed.
_BUILTIN_IDS: set[str] = set()


def register(ruleset: BaseRuleset, builtin: bool = False) -> None:
    _REGISTRY[ruleset.id] = ruleset
    if builtin:
        _BUILTIN_IDS.add(ruleset.id)


def unregister(ruleset_id: str) -> None:
    """Remove a custom ruleset from the live registry (built-ins are protected)."""
    if ruleset_id in _BUILTIN_IDS:
        return
    _REGISTRY.pop(ruleset_id, None)


def is_registered(ruleset_id: str) -> bool:
    return ruleset_id in _REGISTRY


def is_builtin(ruleset_id: str) -> bool:
    return ruleset_id in _BUILTIN_IDS


def get_ruleset(ruleset_id: str) -> BaseRuleset:
    ruleset = _REGISTRY.get(ruleset_id)
    if ruleset is None:
        raise NotFoundError(f"Unknown ruleset: {ruleset_id}")
    return ruleset


def list_rulesets() -> list[dict]:
    """Return metadata for all registered rulesets (built-in + custom)."""
    return [
        {
            "id": rs.id,
            "name": rs.name,
            "description": rs.description,
            "status": "available",
            "custom": rs.id not in _BUILTIN_IDS,
        }
        for rs in _REGISTRY.values()
    ]


def register_custom(model) -> BaseRuleset:
    """Register (or replace) a custom ruleset from a CustomRuleset DB row."""
    from app.rulesets.dynamic import DynamicRuleset

    ruleset = DynamicRuleset.from_model(model)
    register(ruleset)
    return ruleset


async def load_custom_rulesets(session) -> int:
    """Load all active custom rulesets from the DB into the live registry."""
    from sqlalchemy import select

    from app.db.models import CustomRuleset

    rows = (
        await session.execute(
            select(CustomRuleset).where(CustomRuleset.is_active == True)  # noqa: E712
        )
    ).scalars().all()
    for row in rows:
        register_custom(row)
    return len(rows)


# Auto-register built-in rulesets on import.
register(GenericRuleset(), builtin=True)
register(DnD5eRuleset(), builtin=True)
register(OneRingRuleset(), builtin=True)
register(AlienRPGRuleset(), builtin=True)
