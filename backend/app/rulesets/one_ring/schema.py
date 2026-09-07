"""Pydantic models for The One Ring-style ruleset.

Mechanics only (a d12 "feat" die plus a pool of d6 "success" dice resolved
against a target number). No copyrighted setting or rulebook text is included.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

# Feat die special faces (mechanics, not copyrighted names).
FEAT_ILL_OMEN = 11  # counts as 0; an ill omen
FEAT_GREAT = 12  # an automatic, auspicious success


class OneRingRulesetConfig(BaseModel):
    default_tn: int = 14
    feat_die: str = "1d12"
    success_die: str = "1d6"
    default_skill_rank: int = 2
    six_is_notable: bool = True  # a 6 on a success die marks a greater success


class OneRingCharacterData(BaseModel):
    """Shape of Character.ruleset_data for The One Ring ruleset."""

    culture: str = "Wanderer"
    calling: str = "Wanderer"
    attributes: dict[str, int] = Field(
        default_factory=lambda: {"Strength": 4, "Heart": 4, "Wits": 4}
    )
    skills: dict[str, int] = Field(default_factory=dict)  # skill -> rank (0-6)
    resources: dict[str, dict] = Field(
        default_factory=lambda: {
            "Endurance": {"current": 20, "max": 20},
            "Hope": {"current": 8, "max": 8},
            "Shadow": {"current": 0, "max": 20},
        }
    )
