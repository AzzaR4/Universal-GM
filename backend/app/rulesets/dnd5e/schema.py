"""Pydantic models for the D&D 5e-style ruleset.

These describe generic d20 mechanics (ability scores, modifiers, proficiency,
AC, HP, hit dice, spell slots). No copyrighted rulebook text is used — only the
open, mathematical structure of a d20 system.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

ABILITIES = ["str", "dex", "con", "int", "wis", "cha"]
ABILITY_NAMES = {
    "str": "Strength",
    "dex": "Dexterity",
    "con": "Constitution",
    "int": "Intelligence",
    "wis": "Wisdom",
    "cha": "Charisma",
}

# Skill -> governing ability (open d20 structure).
SKILL_ABILITY = {
    "Acrobatics": "dex",
    "Animal Handling": "wis",
    "Arcana": "int",
    "Athletics": "str",
    "Deception": "cha",
    "History": "int",
    "Insight": "wis",
    "Intimidation": "cha",
    "Investigation": "int",
    "Medicine": "wis",
    "Nature": "int",
    "Perception": "wis",
    "Performance": "cha",
    "Persuasion": "cha",
    "Religion": "int",
    "Sleight of Hand": "dex",
    "Stealth": "dex",
    "Survival": "wis",
}


def ability_modifier(score: int) -> int:
    """Standard d20 ability modifier: floor((score - 10) / 2)."""
    return (score - 10) // 2


def proficiency_bonus_for_level(level: int) -> int:
    """Open d20 proficiency progression: +2 at L1, +1 every 4 levels."""
    return 2 + max(0, (level - 1) // 4)


class DnD5eRulesetConfig(BaseModel):
    default_ability_score: int = 10
    starting_level: int = 1
    default_ac: int = 12
    default_hp: int = 10
    use_death_saves: bool = True
    crit_on: int = 20  # natural roll that crits
    fumble_on: int = 1  # natural roll that auto-fails


class DnD5eCharacterData(BaseModel):
    """Shape of Character.ruleset_data for the D&D 5e ruleset."""

    char_class: str = "Fighter"
    level: int = 1
    proficiency_bonus: int = 2
    abilities: dict[str, int] = Field(default_factory=dict)  # str/dex/... -> score
    proficient_skills: list[str] = Field(default_factory=list)
    proficient_saves: list[str] = Field(default_factory=list)  # ability keys
    armor_class: int = 12
    resources: dict[str, dict] = Field(default_factory=dict)  # HP -> {current,max}
    hit_dice: str = "1d10"
    spell_slots: dict[str, dict] = Field(default_factory=dict)  # "1" -> {current,max}
