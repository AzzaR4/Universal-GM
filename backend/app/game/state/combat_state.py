"""Combat state model — a lightweight, serialisable encounter tracker.

Combat state is stored as JSON on Campaign.active_combat (NULL when no encounter
is running). It is intentionally ruleset-agnostic: initiative ordering is derived
per-ruleset via BaseRuleset.get_initiative, but the tracker itself only stores
combatant ids, HP, initiative, and turn order.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Combatant:
    id: str
    name: str
    is_player: bool
    initiative: int = 10
    hp_current: int = 0
    hp_max: int = 0
    resource: str = "HP"
    status: str = "alive"  # alive | defeated
    is_npc: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Combatant":
        allowed = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class CombatState:
    active: bool = True
    round: int = 1
    turn_index: int = 0
    combatants: list[Combatant] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    def order(self) -> list[Combatant]:
        """Combatants sorted by descending initiative (stable for ties)."""
        return sorted(self.combatants, key=lambda c: c.initiative, reverse=True)

    def current_combatant(self) -> Combatant | None:
        ordered = self.order()
        if not ordered:
            return None
        return ordered[self.turn_index % len(ordered)]

    def get(self, combatant_id: str) -> Combatant | None:
        return next((c for c in self.combatants if c.id == combatant_id), None)

    def living(self) -> list[Combatant]:
        return [c for c in self.combatants if c.status == "alive"]

    def advance_turn(self) -> None:
        """Advance to the next living combatant, incrementing round as needed."""
        ordered = self.order()
        if not ordered:
            return
        n = len(ordered)
        for _ in range(n):
            self.turn_index += 1
            if self.turn_index >= n:
                self.turn_index = 0
                self.round += 1
            nxt = ordered[self.turn_index % n]
            if nxt.status == "alive":
                break

    def is_over(self) -> bool:
        players = [c for c in self.living() if c.is_player]
        enemies = [c for c in self.living() if not c.is_player]
        return not players or not enemies

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "round": self.round,
            "turn_index": self.turn_index,
            "combatants": [c.to_dict() for c in self.combatants],
            "log": self.log,
            "current_id": (self.current_combatant().id if self.current_combatant() else None),
            "is_over": self.is_over(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CombatState | None":
        if not data:
            return None
        return cls(
            active=data.get("active", True),
            round=data.get("round", 1),
            turn_index=data.get("turn_index", 0),
            combatants=[Combatant.from_dict(c) for c in data.get("combatants", [])],
            log=list(data.get("log", [])),
        )
