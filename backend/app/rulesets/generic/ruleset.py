"""The Generic ruleset — the first fully-functional vertical slice ruleset.

Rules-light resolution uses a single 2d6 roll mapped to broad outcomes:
    12        -> critical_success
    8-11      -> success
    5-7       -> partial
    2-4       -> failure
(2 with default dice is the floor; treated as failure/critical_failure boundary)
"""
from __future__ import annotations

import random
from typing import Any

from app.core.exceptions import RuleViolationError
from app.game.rules.base_ruleset import ActionIntent, ActionResult, BaseRuleset
from app.game.rules.dice import roll_dice
from app.game.state.game_state import (
    AddConditionMutation,
    DamageMutation,
    GameState,
    MoveMutation,
    StateMutation,
)
from app.rulesets.generic.prompts import build_gm_system
from app.rulesets.generic.schema import GenericRulesetConfig

OUTCOME_LABELS = {
    "critical_success": "Critical Success",
    "success": "Success",
    "partial": "Partial Success",
    "failure": "Failure",
    "critical_failure": "Critical Failure",
    "none": "No Check",
}

# Action types that require a mechanical check in rules-light mode.
_CHECK_ACTIONS = {"attack", "skill_check", "use_item"}
# Action types that never require a check.
_NO_CHECK_ACTIONS = {"move", "talk", "examine", "other"}


class GenericRuleset(BaseRuleset):
    id = "generic"
    name = "Generic (Rules-Light)"
    description = (
        "A flexible, system-agnostic ruleset supporting rules-heavy, rules-light, "
        "and narrative-only play. Uses a single 2d6 roll for broad outcomes."
    )

    def default_config(self) -> dict[str, Any]:
        return GenericRulesetConfig().model_dump()

    def character_schema(self) -> dict[str, Any]:
        cfg = GenericRulesetConfig()
        return {
            "attributes": [a.model_dump() for a in cfg.attributes],
            "resources": [r.model_dump() for r in cfg.resources],
            "skills": [s.model_dump() for s in cfg.skills],
            "conditions": [c.model_dump() for c in cfg.conditions],
        }

    def new_character_data(self, config: dict[str, Any]) -> dict[str, Any]:
        cfg = GenericRulesetConfig(**(config or {}))
        attributes = {a.name: a.default for a in cfg.attributes}
        skills = {s.name: 0 for s in cfg.skills}
        resources = {r.name: {"current": r.default, "max": r.max} for r in cfg.resources}
        return {"attributes": attributes, "skills": skills, "resources": resources}

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def validate_action(self, intent: ActionIntent, state: GameState) -> None:
        actor = None
        if intent.actor_id:
            actor = state.get_character(intent.actor_id)
        else:
            actor = state.get_player_character()
        if actor is None:
            raise RuleViolationError("No acting character found for this action.")
        if not actor.is_alive:
            raise RuleViolationError(
                f"{actor.name} is {actor.status} and cannot take actions."
            )
        if intent.action_type == "move" and intent.target_location_id:
            if state.get_location(intent.target_location_id) is None:
                raise RuleViolationError("Destination location does not exist.")
        if intent.action_type == "attack" and intent.target_id:
            target = state.get_character(intent.target_id)
            target_npc = next((n for n in state.npcs if n.id == intent.target_id), None)
            if target is None and target_npc is None:
                raise RuleViolationError("Attack target does not exist.")

    # ------------------------------------------------------------------ #
    # Resolution
    # ------------------------------------------------------------------ #
    def resolve_action(
        self, intent: ActionIntent, state: GameState, rng: random.Random | None = None
    ) -> ActionResult:
        config = GenericRulesetConfig(**(state.ruleset_config or {}))
        actor = state.get_character(intent.actor_id) if intent.actor_id else state.get_player_character()

        # Narrative-only mode: never roll.
        if config.resolution_mode == "narrative_only" or intent.action_type in _NO_CHECK_ACTIONS:
            return self._resolve_no_check(intent, state, actor)

        if not config.use_dice:
            return self._resolve_no_check(intent, state, actor)

        # Perform a 2d6 (or configured) roll.
        dice = roll_dice(config.default_dice, rng=rng)
        outcome = self._map_outcome(dice.total)
        result = ActionResult(
            intent=intent,
            check_required=True,
            dice_rolled=dice.to_dict(),
            outcome=outcome,
            outcome_label=OUTCOME_LABELS[outcome],
        )
        result.mechanical_description = self._describe(intent, outcome, actor)
        result.state_mutations = self._mutations_for(intent, outcome, state, actor)
        return result

    def _resolve_no_check(
        self, intent: ActionIntent, state: GameState, actor
    ) -> ActionResult:
        mutations: list[StateMutation] = []
        outcome = "none"
        desc = "No mechanical check required; narration resolves this action."
        if intent.action_type == "move" and intent.target_location_id and actor:
            mutations.append(
                MoveMutation(character_id=actor.id, to_location_id=intent.target_location_id)
            )
            desc = f"{actor.name} moves to a new location."
        return ActionResult(
            intent=intent,
            check_required=False,
            dice_rolled=None,
            outcome=outcome,
            outcome_label=OUTCOME_LABELS[outcome],
            mechanical_description=desc,
            state_mutations=mutations,
        )

    @staticmethod
    def _map_outcome(total: int) -> str:
        if total >= 12:
            return "critical_success"
        if total >= 8:
            return "success"
        if total >= 5:
            return "partial"
        if total <= 2:
            return "critical_failure"
        return "failure"

    @staticmethod
    def _describe(intent: ActionIntent, outcome: str, actor) -> str:
        name = actor.name if actor else "The character"
        verb = {
            "attack": "attacks",
            "skill_check": "attempts",
            "use_item": "uses an item",
        }.get(intent.action_type, "acts")
        return f"{name} {verb} — {OUTCOME_LABELS[outcome]}."

    def _mutations_for(
        self, intent: ActionIntent, outcome: str, state: GameState, actor
    ) -> list[StateMutation]:
        mutations: list[StateMutation] = []
        if intent.action_type == "attack" and intent.target_id:
            damage = {
                "critical_success": 4,
                "success": 3,
                "partial": 1,
                "failure": 0,
                "critical_failure": 0,
            }.get(outcome, 0)
            if damage > 0:
                mutations.append(
                    DamageMutation(character_id=intent.target_id, resource="Health", amount=damage)
                )
            # On a critical failure attacking, the actor stumbles and is Wounded.
            if outcome == "critical_failure" and actor:
                mutations.append(AddConditionMutation(character_id=actor.id, condition="Wounded"))
        elif intent.action_type in {"skill_check", "use_item"}:
            if outcome == "critical_failure" and actor:
                mutations.append(AddConditionMutation(character_id=actor.id, condition="Wounded"))
        return mutations

    def system_prompt_fragment(self, state: GameState) -> str:
        gm_cfg = dict(state.gm_config or {})
        gm_cfg.setdefault("campaign_style", "")
        return build_gm_system(state.ruleset_config or {}, gm_cfg)
