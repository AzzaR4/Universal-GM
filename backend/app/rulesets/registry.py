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


def register(ruleset: BaseRuleset) -> None:
    _REGISTRY[ruleset.id] = ruleset


def get_ruleset(ruleset_id: str) -> BaseRuleset:
    ruleset = _REGISTRY.get(ruleset_id)
    if ruleset is None:
        raise NotFoundError(f"Unknown ruleset: {ruleset_id}")
    return ruleset


def list_rulesets() -> list[dict]:
    """Return metadata for all registered rulesets (all now available)."""
    return [
        {"id": rs.id, "name": rs.name, "description": rs.description, "status": "available"}
        for rs in _REGISTRY.values()
    ]


# Auto-register built-in rulesets on import.
register(GenericRuleset())
register(DnD5eRuleset())
register(OneRingRuleset())
register(AlienRPGRuleset())
