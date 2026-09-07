"""The One Ring-style ruleset.

Resolution: roll one feat die (d12) plus a pool of success dice (Nd6, where N is
the character's rank in the relevant skill). Sum them and compare to a Target
Number (TN, default 14).

  * Feat die 12 -> an auspicious result: automatic success.
  * Feat die 11 -> an ill omen: the feat die counts as 0. If the character is
    Miserable, an ill omen turns the roll into a critical failure.
  * Success dice showing a 6 are "notable"; two or more sixes on a success mark a
    great (critical) success.
  * Weary characters count success dice showing 1-3 as 0.

Resources: Endurance (stamina), Hope (spent to push on), Shadow (corruption).
No copyrighted setting or rulebook text is used — only the dice mechanics.
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
from app.rulesets.one_ring.prompts import build_gm_system
from app.rulesets.one_ring.schema import (
    FEAT_GREAT,
    FEAT_ILL_OMEN,
    OneRingCharacterData,
    OneRingRulesetConfig,
)

OUTCOME_LABELS = {
    "critical_success": "Great Success",
    "success": "Success",
    "partial": "Partial Success",
    "failure": "Failure",
    "critical_failure": "Ill Fate",
    "none": "No Roll",
}

_NO_CHECK_ACTIONS = {"move", "talk", "examine", "other"}


class OneRingRuleset(BaseRuleset):
    id = "one_ring"
    name = "The One Ring (Feat + Success Dice)"
    description = (
        "A Middle-earth-inspired adventuring system: a d12 feat die plus a pool of "
        "d6 success dice resolved against a target number, with Hope, Shadow, and "
        "Endurance resources."
    )

    def default_config(self) -> dict[str, Any]:
        return OneRingRulesetConfig().model_dump()

    def character_schema(self) -> dict[str, Any]:
        return {
            "attributes": [
                {"name": "Strength", "default": 4},
                {"name": "Heart", "default": 4},
                {"name": "Wits", "default": 4},
            ],
            "fields": [
                {"key": "culture", "label": "Culture", "type": "string"},
                {"key": "calling", "label": "Calling", "type": "string"},
            ],
            "resources": [
                {"name": "Endurance", "abbreviation": "END"},
                {"name": "Hope", "abbreviation": "HOPE"},
                {"name": "Shadow", "abbreviation": "SHDW"},
            ],
            "conditions": [
                {"name": "Weary", "description": "Success dice showing 1-3 count as 0."},
                {"name": "Miserable", "description": "An ill omen (feat die 11) causes ill fate."},
            ],
        }

    def new_character_data(self, config: dict[str, Any]) -> dict[str, Any]:
        return OneRingCharacterData().model_dump()

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
        config = OneRingRulesetConfig(**(state.ruleset_config or {}))
        actor = (
            state.get_character(intent.actor_id)
            if intent.actor_id
            else state.get_player_character()
        )

        if intent.action_type in _NO_CHECK_ACTIONS:
            return self._resolve_no_check(intent, actor)

        return self._resolve_roll(intent, state, actor, config, rng)

    def _resolve_no_check(self, intent: ActionIntent, actor) -> ActionResult:
        mutations: list[StateMutation] = []
        desc = "No roll required; the tale carries on."
        if intent.action_type == "move" and intent.target_location_id and actor:
            mutations.append(
                MoveMutation(character_id=actor.id, to_location_id=intent.target_location_id)
            )
            desc = f"{actor.name} travels onward."
        return ActionResult(
            intent=intent,
            check_required=False,
            dice_rolled=None,
            outcome="none",
            outcome_label=OUTCOME_LABELS["none"],
            mechanical_description=desc,
            state_mutations=mutations,
        )

    def _skill_rank(self, intent: ActionIntent, actor, config) -> int:
        if intent.metadata and "skill_rank" in intent.metadata:
            return max(0, int(intent.metadata["skill_rank"]))
        if actor and intent.skill_used:
            skills = (actor.ruleset_data or {}).get("skills", {})
            if intent.skill_used in skills:
                return max(0, int(skills[intent.skill_used]))
        return config.default_skill_rank

    @staticmethod
    def _is_weary(actor) -> bool:
        return bool(actor) and "Weary" in (actor.conditions or [])

    @staticmethod
    def _is_miserable(actor) -> bool:
        return bool(actor) and "Miserable" in (actor.conditions or [])

    def _resolve_roll(self, intent, state, actor, config, rng) -> ActionResult:
        rank = self._skill_rank(intent, actor, config)
        tn = int((intent.metadata or {}).get("tn", config.default_tn))
        weary = self._is_weary(actor)
        miserable = self._is_miserable(actor)

        feat = roll_dice(config.feat_die, rng=rng)
        feat_value = feat.rolls[0]

        success_rolls: list[int] = []
        for _ in range(rank):
            success_rolls.append(roll_dice(config.success_die, rng=rng).rolls[0])

        # Apply Weary: 1-3 count as 0.
        counted = [v if not (weary and v <= 3) else 0 for v in success_rolls]
        sixes = sum(1 for v in success_rolls if v == 6)

        auto_success = feat_value == FEAT_GREAT
        ill_omen = feat_value == FEAT_ILL_OMEN
        feat_contribution = 0 if (ill_omen or auto_success) else feat_value
        total = feat_contribution + sum(counted)

        if ill_omen and miserable:
            outcome = "critical_failure"
        elif auto_success:
            outcome = "critical_success" if sixes >= 1 else "success"
        elif total >= tn:
            outcome = "critical_success" if sixes >= 2 else "success"
        elif ill_omen:
            outcome = "failure"
        else:
            outcome = "failure"

        name = actor.name if actor else "The hero"
        dice_dict = {
            "notation": f"{config.feat_die} + {rank}{config.success_die}",
            "num_dice": 1 + rank,
            "sides": 12,
            "modifier": 0,
            "rolls": [feat_value] + success_rolls,
            "total": total,
            "feat_die": feat_value,
            "success_dice": success_rolls,
            "sixes": sixes,
            "tn": tn,
            "ill_omen": ill_omen,
            "auto_success": auto_success,
            "weary": weary,
        }

        mutations: list[StateMutation] = []
        detail_bits = []
        if auto_success:
            detail_bits.append("an auspicious feat die (12)")
        if ill_omen:
            detail_bits.append("an ill omen (feat die 11 counts as 0)")
        if sixes:
            detail_bits.append(f"{sixes} notable six{'es' if sixes != 1 else ''}")
        detail = f" — {', '.join(detail_bits)}" if detail_bits else ""

        if intent.action_type == "attack" and intent.target_id and outcome in {
            "success",
            "critical_success",
        }:
            damage_dice = (intent.metadata or {}).get("damage_dice", "1d6")
            dmg = roll_dice(damage_dice, rng=rng).total
            if outcome == "critical_success":
                dmg *= 2
            mutations.append(
                DamageMutation(character_id=intent.target_id, resource="Endurance", amount=dmg)
            )
            detail += f"; the blow costs the foe {dmg} Endurance"

        # An ill fate while miserable deepens the Shadow on the actor.
        if outcome == "critical_failure" and actor:
            mutations.append(AddConditionMutation(character_id=actor.id, condition="Weary"))

        skill_label = intent.skill_used or intent.action_type
        result = ActionResult(
            intent=intent,
            check_required=True,
            dice_rolled=dice_dict,
            outcome=outcome,
            outcome_label=OUTCOME_LABELS[outcome],
            mechanical_description=(
                f"{name} attempts {skill_label} (TN {tn}) — rolled {total}{detail}. "
                f"{OUTCOME_LABELS[outcome]}."
            ),
            state_mutations=mutations,
        )
        return result

    def system_prompt_fragment(self, state: GameState) -> str:
        return build_gm_system(state.ruleset_config or {}, dict(state.gm_config or {}))
