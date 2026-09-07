"""Alien RPG-style ruleset (Year Zero Engine).

Resolution: build a pool of d6s equal to (attribute + skill). Each die showing a
6 is a success; one success is enough to succeed, more successes make it better.

Stress: the character's current Stress adds that many bonus dice to the pool.
Any Stress die showing a 1 is a "bane" that risks Panic. Pushing a roll rerolls
all failed dice once and raises Stress by 1 (the push flag is carried in intent
metadata). No copyrighted setting or rulebook text is used — only the mechanics.
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
    HealMutation,
    MoveMutation,
    StateMutation,
)
from app.rulesets.alien_rpg.prompts import build_gm_system
from app.rulesets.alien_rpg.schema import (
    SKILL_ATTRIBUTE,
    AlienCharacterData,
    AlienRulesetConfig,
)

OUTCOME_LABELS = {
    "critical_success": "Critical Success",
    "success": "Success",
    "partial": "Partial Success",
    "failure": "Failure",
    "critical_failure": "Catastrophe",
    "none": "No Roll",
}

_NO_CHECK_ACTIONS = {"move", "talk", "examine", "other"}


class AlienRPGRuleset(BaseRuleset):
    id = "alien_rpg"
    name = "Alien RPG (Year Zero Engine)"
    description = (
        "A sci-fi horror system: roll a pool of d6s (attribute + skill), counting "
        "6s as successes, with a Stress mechanic that adds dice at the risk of Panic."
    )

    def default_config(self) -> dict[str, Any]:
        return AlienRulesetConfig().model_dump()

    def character_schema(self) -> dict[str, Any]:
        return {
            "attributes": [
                {"name": a, "default": 3, "min": 1, "max": 5}
                for a in ["Strength", "Agility", "Wits", "Empathy"]
            ],
            "skills": [{"name": s, "attribute": a} for s, a in SKILL_ATTRIBUTE.items()],
            "fields": [{"key": "career", "label": "Career", "type": "string"}],
            "resources": [
                {"name": "Health", "abbreviation": "HP"},
                {"name": "Stress", "abbreviation": "STR"},
            ],
            "conditions": [
                {"name": "Panicking", "description": "Overcome by fear; actions are unreliable."}
            ],
        }

    def new_character_data(self, config: dict[str, Any]) -> dict[str, Any]:
        return AlienCharacterData().model_dump()

    # ------------------------------------------------------------------ #
    # Validation
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
            raise RuleViolationError(f"{actor.name} is {actor.status} and cannot take actions.")
        if intent.action_type == "move" and intent.target_location_id:
            if state.get_location(intent.target_location_id) is None:
                raise RuleViolationError("Destination location does not exist.")

    # ------------------------------------------------------------------ #
    # Resolution
    # ------------------------------------------------------------------ #
    def resolve_action(
        self, intent: ActionIntent, state: GameState, rng: random.Random | None = None
    ) -> ActionResult:
        config = AlienRulesetConfig(**(state.ruleset_config or {}))
        actor = (
            state.get_character(intent.actor_id)
            if intent.actor_id
            else state.get_player_character()
        )

        if intent.action_type in _NO_CHECK_ACTIONS:
            return self._resolve_no_check(intent, actor)

        return self._resolve_pool(intent, actor, config, rng)

    def _resolve_no_check(self, intent: ActionIntent, actor) -> ActionResult:
        mutations: list[StateMutation] = []
        desc = "No roll required; the scene proceeds."
        if intent.action_type == "move" and intent.target_location_id and actor:
            mutations.append(
                MoveMutation(character_id=actor.id, to_location_id=intent.target_location_id)
            )
            desc = f"{actor.name} moves to a new area."
        return ActionResult(
            intent=intent,
            check_required=False,
            dice_rolled=None,
            outcome="none",
            outcome_label=OUTCOME_LABELS["none"],
            mechanical_description=desc,
            state_mutations=mutations,
        )

    def _base_pool(self, intent: ActionIntent, actor, config) -> int:
        meta = intent.metadata or {}
        if "pool" in meta:
            return max(1, int(meta["pool"]))
        attr_val = 0
        skill_val = 0
        data = (actor.ruleset_data or {}) if actor else {}
        attrs = data.get("attributes", {})
        skills = data.get("skills", {})
        skill = intent.skill_used or ""
        attr_name = SKILL_ATTRIBUTE.get(skill)
        if attr_name and attr_name in attrs:
            attr_val = int(attrs[attr_name])
        elif attrs:
            attr_val = int(next(iter(attrs.values())))
        if skill and skill in skills:
            skill_val = int(skills[skill])
        pool = attr_val + skill_val
        return max(1, pool)

    @staticmethod
    def _current_stress(actor) -> int:
        data = (actor.ruleset_data or {}) if actor else {}
        res = data.get("resources", {}).get("Stress", {})
        return int(res.get("current", 0))

    def _resolve_pool(self, intent, actor, config, rng) -> ActionResult:
        meta = intent.metadata or {}
        base_pool = self._base_pool(intent, actor, config)
        stress = self._current_stress(actor)
        pushed = bool(meta.get("push", False)) and config.allow_push

        base_rolls = [roll_dice(config.die, rng=rng).rolls[0] for _ in range(base_pool)]
        stress_rolls = [roll_dice(config.die, rng=rng).rolls[0] for _ in range(stress)]

        added_stress = 0
        if pushed:
            # Reroll every die that is not already a success (a 6), once.
            base_rolls = [
                r if r == config.success_on else roll_dice(config.die, rng=rng).rolls[0]
                for r in base_rolls
            ]
            stress_rolls = [
                r if r == config.success_on else roll_dice(config.die, rng=rng).rolls[0]
                for r in stress_rolls
            ]
            added_stress = 1
            # A push adds one Stress die to the pool as well.
            stress_rolls.append(roll_dice(config.die, rng=rng).rolls[0])

        successes = sum(1 for r in base_rolls + stress_rolls if r == config.success_on)
        banes = sum(1 for r in stress_rolls if r == config.bane_on)
        panic = banes > 0

        if successes >= 3:
            outcome = "critical_success"
        elif successes >= 1:
            outcome = "success"
        elif panic:
            outcome = "critical_failure"
        else:
            outcome = "failure"

        name = actor.name if actor else "The crew member"
        dice_dict = {
            "notation": f"{base_pool}{config.die}"
            + (f" + {len(stress_rolls)} stress" if stress_rolls else ""),
            "num_dice": len(base_rolls) + len(stress_rolls),
            "sides": 6,
            "modifier": 0,
            "rolls": base_rolls + stress_rolls,
            "total": successes,
            "base_dice": base_rolls,
            "stress_dice": stress_rolls,
            "successes": successes,
            "banes": banes,
            "pushed": pushed,
            "panic": panic,
        }

        mutations: list[StateMutation] = []
        detail_bits = [f"{successes} success{'es' if successes != 1 else ''}"]
        if pushed:
            detail_bits.append("pushed (+1 Stress)")
        if panic:
            detail_bits.append(f"{banes} bane — Panic risk!")

        if added_stress and actor:
            mutations.append(
                HealMutation(character_id=actor.id, resource="Stress", amount=added_stress)
            )
        if panic and actor:
            mutations.append(AddConditionMutation(character_id=actor.id, condition="Panicking"))

        if intent.action_type == "attack" and intent.target_id and successes >= 1:
            base_damage = int(meta.get("base_damage", 1))
            damage = base_damage + (successes - 1)
            mutations.append(
                DamageMutation(character_id=intent.target_id, resource="Health", amount=damage)
            )
            detail_bits.append(f"{damage} damage to the target")

        skill_label = intent.skill_used or intent.action_type
        result = ActionResult(
            intent=intent,
            check_required=True,
            dice_rolled=dice_dict,
            outcome=outcome,
            outcome_label=OUTCOME_LABELS[outcome],
            mechanical_description=(
                f"{name} rolls {dice_dict['num_dice']} dice for {skill_label} — "
                f"{', '.join(detail_bits)}. {OUTCOME_LABELS[outcome]}."
            ),
            state_mutations=mutations,
        )
        return result

    def system_prompt_fragment(self, state: GameState) -> str:
        return build_gm_system(state.ruleset_config or {}, dict(state.gm_config or {}))
