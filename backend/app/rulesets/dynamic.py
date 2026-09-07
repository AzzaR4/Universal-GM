"""DynamicRuleset — adapts a DB-stored CustomRuleset into a BaseRuleset.

This lets users define new game systems entirely through the Ruleset Builder UI
(dice formula, roll mode, attributes, resources, skills, GM instructions) and
have them behave like the built-in rulesets at runtime — no code changes needed.
"""
from __future__ import annotations

import random
from typing import Any

from app.core.exceptions import RuleViolationError
from app.game.rules.base_ruleset import ActionIntent, ActionResult, BaseRuleset
from app.game.rules.dice import roll_dice
from app.game.state.game_state import DamageMutation, GameState, StateMutation

OUTCOME_LABELS = {
    "critical_success": "Critical Success",
    "success": "Success",
    "partial": "Partial Success",
    "failure": "Failure",
    "critical_failure": "Critical Failure",
    "none": "No Check",
}

_CHECK_ACTIONS = {"attack", "skill_check", "use_item"}
_NO_CHECK_ACTIONS = {"move", "talk", "examine", "other"}


class DynamicRuleset(BaseRuleset):
    """A ruleset whose behaviour is described by data rather than code."""

    def __init__(self, spec: dict[str, Any]) -> None:
        self.id = spec["name"]
        self.name = spec.get("display_name") or spec["name"]
        self.description = spec.get("description", "")
        self.dice_formula = spec.get("dice_formula", "1d20") or "1d20"
        self.roll_mode = spec.get("roll_mode", "single") or "single"
        self.success_threshold = int(spec.get("success_threshold", 6) or 6)
        self._attributes = spec.get("attributes") or []
        self._resources = spec.get("resources") or []
        self._skills = spec.get("skills") or []
        self.prompt_instructions = spec.get("prompt_instructions", "")

    @classmethod
    def from_model(cls, model) -> "DynamicRuleset":
        return cls(
            {
                "name": model.name,
                "display_name": model.display_name,
                "description": model.description,
                "dice_formula": model.dice_formula,
                "roll_mode": model.roll_mode,
                "success_threshold": model.success_threshold,
                "attributes": model.attributes,
                "resources": model.resources,
                "skills": model.skills,
                "prompt_instructions": model.prompt_instructions,
            }
        )

    # ------------------------------------------------------------------ #
    # Schema / config
    # ------------------------------------------------------------------ #
    def default_config(self) -> dict[str, Any]:
        return {
            "dice_formula": self.dice_formula,
            "roll_mode": self.roll_mode,
            "success_threshold": self.success_threshold,
        }

    def character_schema(self) -> dict[str, Any]:
        return {
            "attributes": self._attributes,
            "resources": self._resources,
            "skills": self._skills,
            "conditions": [],
        }

    def new_character_data(self, config: dict[str, Any]) -> dict[str, Any]:
        attributes = {
            a.get("name"): a.get("default", 0)
            for a in self._attributes
            if a.get("name")
        }
        skills = {s.get("name"): 0 for s in self._skills if s.get("name")}
        resources = {}
        for r in self._resources:
            name = r.get("name")
            if not name:
                continue
            mx = r.get("max", 10)
            current = r.get("default", mx)
            resources[name] = {"current": current, "max": mx}
        return {"attributes": attributes, "skills": skills, "resources": resources}

    # ------------------------------------------------------------------ #
    # Validation & resolution
    # ------------------------------------------------------------------ #
    def validate_action(self, intent: ActionIntent, state: GameState) -> None:
        actor = (
            state.get_character(intent.actor_id)
            if intent.actor_id
            else state.get_player_character()
        )
        if actor is None:
            raise RuleViolationError("No acting character found for this action.")
        if not actor.is_alive:
            raise RuleViolationError(
                f"{actor.name} is {actor.status} and cannot take actions."
            )

    def resolve_action(
        self, intent: ActionIntent, state: GameState, rng: random.Random | None = None
    ) -> ActionResult:
        actor = (
            state.get_character(intent.actor_id)
            if intent.actor_id
            else state.get_player_character()
        )
        if intent.action_type in _NO_CHECK_ACTIONS:
            return ActionResult(
                intent=intent,
                check_required=False,
                outcome="none",
                outcome_label=OUTCOME_LABELS["none"],
                mechanical_description="No mechanical check required.",
            )

        dice = roll_dice(self.dice_formula, rng=rng)
        outcome, detail = self._map_outcome(dice)
        result = ActionResult(
            intent=intent,
            check_required=True,
            dice_rolled={**dice.to_dict(), **detail},
            outcome=outcome,
            outcome_label=OUTCOME_LABELS[outcome],
        )
        name = actor.name if actor else "The character"
        result.mechanical_description = f"{name} acts — {OUTCOME_LABELS[outcome]}."
        result.state_mutations = self._mutations_for(intent, outcome, rng)
        return result

    def _map_outcome(self, dice) -> tuple[str, dict]:
        if self.roll_mode == "pool_count_successes":
            successes = sum(1 for r in dice.rolls if r >= self.success_threshold)
            detail = {"successes": successes, "success_threshold": self.success_threshold}
            if successes == 0:
                return "failure", detail
            if successes == 1:
                return "partial", detail
            if successes >= 3:
                return "critical_success", detail
            return "success", detail

        # "single" and "pool_sum" both compare a total against the threshold.
        total = dice.total
        detail = {"total": total, "success_threshold": self.success_threshold}
        max_total = dice.num_dice * dice.sides + dice.modifier
        min_total = dice.num_dice + dice.modifier
        if total >= self.success_threshold + 4 or total == max_total:
            return "critical_success", detail
        if total >= self.success_threshold:
            return "success", detail
        if total >= self.success_threshold - 3:
            return "partial", detail
        if total == min_total:
            return "critical_failure", detail
        return "failure", detail

    def _mutations_for(
        self, intent: ActionIntent, outcome: str, rng=None
    ) -> list[StateMutation]:
        mutations: list[StateMutation] = []
        if intent.action_type == "attack" and intent.target_id:
            if outcome in {"success", "critical_success", "partial"}:
                dmg = roll_dice("1d6", rng=rng).total
                if outcome == "critical_success":
                    dmg *= 2
                elif outcome == "partial":
                    dmg = max(1, dmg // 2)
                # Damage the first defined resource, else "Health".
                resource = "Health"
                if self._resources:
                    resource = self._resources[0].get("name", "Health")
                mutations.append(
                    DamageMutation(
                        character_id=intent.target_id, resource=resource, amount=dmg
                    )
                )
        return mutations

    def get_initiative(self, character_data: dict[str, Any]) -> int:
        attrs = (character_data or {}).get("attributes", {})
        for key in ("Agility", "AGI", "Dexterity", "Speed", "Reflexes"):
            if key in attrs:
                try:
                    return int(attrs[key])
                except (TypeError, ValueError):
                    return 10
        return 10

    def system_prompt_fragment(self, state: GameState) -> str:
        parts = [
            f"You are running a custom tabletop RPG system called '{self.name}'.",
        ]
        if self.description:
            parts.append(self.description)
        parts.append(
            f"Resolution: roll {self.dice_formula} ({self.roll_mode}); "
            f"success threshold {self.success_threshold}."
        )
        if self.prompt_instructions:
            parts.append(self.prompt_instructions)
        return "\n".join(parts)
