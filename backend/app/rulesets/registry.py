"""Ruleset registry with auto-registration.

New rulesets register themselves here. The API exposes the list so the UI can
present available systems. Only the Generic ruleset is fully implemented in the
first vertical slice; placeholders advertise future systems.
"""
from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.game.rules.base_ruleset import BaseRuleset
from app.rulesets.generic.ruleset import GenericRuleset

_REGISTRY: dict[str, BaseRuleset] = {}


def register(ruleset: BaseRuleset) -> None:
    _REGISTRY[ruleset.id] = ruleset


def get_ruleset(ruleset_id: str) -> BaseRuleset:
    ruleset = _REGISTRY.get(ruleset_id)
    if ruleset is None:
        raise NotFoundError(f"Unknown ruleset: {ruleset_id}")
    return ruleset


def list_rulesets() -> list[dict]:
    """Return metadata for all registered + advertised rulesets."""
    implemented = [
        {"id": rs.id, "name": rs.name, "description": rs.description, "status": "available"}
        for rs in _REGISTRY.values()
    ]
    placeholders = [
        {"id": "dnd5e", "name": "D&D 5e (coming soon)", "description": "d20 system adapter.", "status": "planned"},
        {"id": "one_ring", "name": "The One Ring (coming soon)", "description": "Middle-earth adventuring.", "status": "planned"},
        {"id": "alien", "name": "Alien RPG (coming soon)", "description": "Sci-fi horror, stress dice.", "status": "planned"},
    ]
    return implemented + placeholders


# Auto-register built-in rulesets on import.
register(GenericRuleset())
