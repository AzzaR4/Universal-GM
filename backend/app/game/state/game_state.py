"""In-memory representation of the authoritative game state and typed mutations.

The GameState is a read model assembled from the database for the Rules Engine
and Narrative Engine to reason about. It is NEVER mutated directly by the AI.
All changes are expressed as typed StateMutation objects produced by the Rules
Engine and applied by the StateManager.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class CharacterView:
    id: str
    name: str
    description: str
    is_player_character: bool
    ruleset_data: dict[str, Any]
    conditions: list[Any]
    inventory: list[Any]
    location_id: str | None
    status: str

    @property
    def is_alive(self) -> bool:
        return self.status == "alive"


@dataclass
class NPCView:
    id: str
    name: str
    description: str
    location_id: str | None
    current_activity: str
    status: str
    personality: dict[str, Any] = field(default_factory=dict)


@dataclass
class LocationView:
    id: str
    name: str
    description: str
    atmosphere: str


@dataclass
class QuestView:
    id: str
    title: str
    status: str


@dataclass
class GameState:
    campaign_id: str
    campaign_name: str
    ruleset_id: str
    ruleset_config: dict[str, Any]
    gm_config: dict[str, Any]
    current_location_id: str | None
    characters: list[CharacterView] = field(default_factory=list)
    npcs: list[NPCView] = field(default_factory=list)
    locations: list[LocationView] = field(default_factory=list)
    quests: list[QuestView] = field(default_factory=list)

    def get_character(self, character_id: str) -> CharacterView | None:
        return next((c for c in self.characters if c.id == character_id), None)

    def get_player_character(self) -> CharacterView | None:
        return next((c for c in self.characters if c.is_player_character), None)

    def get_location(self, location_id: str | None) -> LocationView | None:
        if not location_id:
            return None
        return next((l for l in self.locations if l.id == location_id), None)

    def npcs_in_location(self, location_id: str | None) -> list[NPCView]:
        if not location_id:
            return []
        return [n for n in self.npcs if n.location_id == location_id]


# --------------------------------------------------------------------------- #
# Typed mutation objects. These are the ONLY way state changes.
# --------------------------------------------------------------------------- #


@dataclass
class StateMutation:
    """Base class for all mutations. `kind` discriminates the subtype."""

    kind: str = "noop"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, **{k: v for k, v in self.__dict__.items() if k != "kind"}}


@dataclass
class DamageMutation(StateMutation):
    kind: Literal["damage"] = "damage"
    character_id: str = ""
    resource: str = "hp"
    amount: int = 0  # positive = damage, applied as subtraction


@dataclass
class HealMutation(StateMutation):
    kind: Literal["heal"] = "heal"
    character_id: str = ""
    resource: str = "hp"
    amount: int = 0


@dataclass
class MoveMutation(StateMutation):
    kind: Literal["move"] = "move"
    character_id: str = ""
    to_location_id: str = ""


@dataclass
class AddConditionMutation(StateMutation):
    kind: Literal["add_condition"] = "add_condition"
    character_id: str = ""
    condition: str = ""


@dataclass
class RemoveConditionMutation(StateMutation):
    kind: Literal["remove_condition"] = "remove_condition"
    character_id: str = ""
    condition: str = ""


@dataclass
class AddInventoryMutation(StateMutation):
    kind: Literal["add_inventory"] = "add_inventory"
    character_id: str = ""
    item: str = ""


@dataclass
class SetStatusMutation(StateMutation):
    kind: Literal["set_status"] = "set_status"
    character_id: str = ""
    status: str = "alive"


def mutation_from_dict(data: dict[str, Any]) -> StateMutation:
    """Reconstruct a mutation object from a serialised dict."""
    kind = data.get("kind", "noop")
    mapping = {
        "damage": DamageMutation,
        "heal": HealMutation,
        "move": MoveMutation,
        "add_condition": AddConditionMutation,
        "remove_condition": RemoveConditionMutation,
        "add_inventory": AddInventoryMutation,
        "set_status": SetStatusMutation,
    }
    cls = mapping.get(kind, StateMutation)
    payload = {k: v for k, v in data.items() if k != "kind"}
    try:
        return cls(**payload)  # type: ignore[arg-type]
    except TypeError:
        return StateMutation()
