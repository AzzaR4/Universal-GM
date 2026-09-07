"""Pydantic models for the Alien RPG-style ruleset (Year Zero Engine).

Mechanics only: a pool of d6s (attribute + skill), successes counted on 6s, with
a Stress mechanic that adds bonus dice at the risk of Panic. No copyrighted
setting or rulebook text is included.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

ATTRIBUTES = ["Strength", "Agility", "Wits", "Empathy"]

# Skill -> governing attribute (open Year Zero structure).
SKILL_ATTRIBUTE = {
    "Heavy Machinery": "Strength",
    "Close Combat": "Strength",
    "Stamina": "Strength",
    "Ranged Combat": "Agility",
    "Mobility": "Agility",
    "Piloting": "Agility",
    "Observation": "Wits",
    "Comtech": "Wits",
    "Survival": "Wits",
    "Command": "Empathy",
    "Manipulation": "Empathy",
    "Medical Aid": "Empathy",
}


class AlienRulesetConfig(BaseModel):
    die: str = "1d6"
    success_on: int = 6
    bane_on: int = 1  # a 1 on a stress die risks panic
    max_stress: int = 10
    allow_push: bool = True


class AlienCharacterData(BaseModel):
    """Shape of Character.ruleset_data for the Alien RPG ruleset."""

    career: str = "Colonial Marine"
    attributes: dict[str, int] = Field(
        default_factory=lambda: {"Strength": 3, "Agility": 3, "Wits": 3, "Empathy": 3}
    )
    skills: dict[str, int] = Field(default_factory=dict)  # skill -> level (0-5)
    resources: dict[str, dict] = Field(
        default_factory=lambda: {
            "Health": {"current": 3, "max": 3},
            "Stress": {"current": 0, "max": 10},
        }
    )
    panic_level: int = 0
