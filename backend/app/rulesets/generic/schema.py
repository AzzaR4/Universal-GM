"""Pydantic models describing Generic ruleset configuration and characters."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AttributeDefinition(BaseModel):
    name: str
    abbreviation: str = ""
    min: int = 1
    max: int = 10
    default: int = 5


class SkillDefinition(BaseModel):
    name: str
    attribute: str = ""


class ResourceDefinition(BaseModel):
    name: str
    abbreviation: str = ""
    default: int = 10
    max: int = 10


class ConditionDefinition(BaseModel):
    name: str
    description: str = ""


class GenericRulesetConfig(BaseModel):
    resolution_mode: Literal["rules_heavy", "rules_light", "narrative_only"] = "rules_light"
    use_dice: bool = True
    default_dice: str = "2d6"
    check_style: Literal["target_number", "opposed", "narrative", "custom"] = "narrative"
    default_difficulty: int = 8
    attributes: list[AttributeDefinition] = Field(
        default_factory=lambda: [
            AttributeDefinition(name="Might", abbreviation="MGT", default=5),
            AttributeDefinition(name="Agility", abbreviation="AGI", default=5),
            AttributeDefinition(name="Wits", abbreviation="WIT", default=5),
            AttributeDefinition(name="Presence", abbreviation="PRE", default=5),
        ]
    )
    skills: list[SkillDefinition] = Field(default_factory=list)
    resources: list[ResourceDefinition] = Field(
        default_factory=lambda: [ResourceDefinition(name="Health", abbreviation="HP", default=10, max=10)]
    )
    conditions: list[ConditionDefinition] = Field(
        default_factory=lambda: [
            ConditionDefinition(name="Wounded", description="Physically hurt; -1 to physical checks"),
            ConditionDefinition(name="Frightened", description="Afraid; -1 to presence checks"),
        ]
    )
    use_combat: bool = True
    combat_style: Literal["structured", "abstract", "narrative"] = "abstract"


class GenericCharacterData(BaseModel):
    """The shape of Character.ruleset_data for the Generic ruleset."""

    attributes: dict[str, int] = Field(default_factory=dict)
    skills: dict[str, int] = Field(default_factory=dict)
    resources: dict[str, dict] = Field(default_factory=dict)  # name -> {current, max}
