"""Abstract ruleset contract and the shared Action data structures.

A ruleset is a stateless plugin that knows how to validate and resolve actions
for a particular game system. The Generic ruleset is the reference impl.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.game.state.game_state import GameState, StateMutation


@dataclass
class ActionIntent:
    """Structured representation of what the player is trying to do.

    Produced by the intent parser (AI JSON-mode) OR mechanically in tests.
    """

    action_type: str = "other"  # attack, skill_check, move, talk, examine, other
    description: str = ""
    actor_id: str | None = None
    skill_used: str | None = None
    target_id: str | None = None
    target_location_id: str | None = None
    raw_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "description": self.description,
            "actor_id": self.actor_id,
            "skill_used": self.skill_used,
            "target_id": self.target_id,
            "target_location_id": self.target_location_id,
            "raw_text": self.raw_text,
            "metadata": self.metadata,
        }


@dataclass
class ActionResult:
    """The authoritative mechanical result of an action."""

    intent: ActionIntent
    check_required: bool = False
    dice_rolled: dict[str, Any] | None = None
    outcome: str = "none"  # critical_success, success, partial, failure, critical_failure, none
    outcome_label: str = ""
    mechanical_description: str = ""
    state_mutations: list[StateMutation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "check_required": self.check_required,
            "dice_rolled": self.dice_rolled,
            "outcome": self.outcome,
            "outcome_label": self.outcome_label,
            "mechanical_description": self.mechanical_description,
            "state_mutations": [m.to_dict() for m in self.state_mutations],
        }


class BaseRuleset(ABC):
    """Abstract base class every ruleset must implement."""

    id: str = "base"
    name: str = "Base Ruleset"
    description: str = ""

    @abstractmethod
    def default_config(self) -> dict[str, Any]:
        """Return the default configuration dict for a new campaign."""

    @abstractmethod
    def character_schema(self) -> dict[str, Any]:
        """Return a JSON-schema-like description of a character for the UI."""

    @abstractmethod
    def new_character_data(self, config: dict[str, Any]) -> dict[str, Any]:
        """Return default ruleset_data for a brand new character."""

    @abstractmethod
    def validate_action(self, intent: ActionIntent, state: GameState) -> None:
        """Raise RuleViolationError if the action is not permitted."""

    @abstractmethod
    def resolve_action(self, intent: ActionIntent, state: GameState) -> ActionResult:
        """Resolve the action mechanically and return an ActionResult."""

    @abstractmethod
    def system_prompt_fragment(self, state: GameState) -> str:
        """Return a GM system-prompt fragment describing how to run this system."""

    # ------------------------------------------------------------------ #
    # Optional hooks with sensible defaults (non-abstract).
    # ------------------------------------------------------------------ #
    def get_initiative(self, character_data: dict[str, Any]) -> int:
        """Return an initiative score for a combatant given its ruleset_data.

        The default is a stable neutral value; system-specific rulesets override
        this to use the appropriate attribute/roll (e.g. DEX modifier for D&D).
        Combatants are ordered by descending initiative.
        """
        return 10
