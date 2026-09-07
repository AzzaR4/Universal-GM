"""D&D 5e-style ruleset — a d20 system adapter.

Implements the open mathematical structure of a d20 game:
  * Attack rolls: 1d20 + ability modifier (+ proficiency) vs target AC
  * Skill checks: 1d20 + ability modifier (+ proficiency if proficient) vs DC
  * Saving throws: 1d20 + ability modifier (+ proficiency if proficient) vs DC
  * HP damage via weapon damage dice; critical hits double the damage dice
  * Natural 20 = critical hit / auto-success; natural 1 = fumble / auto-failure

No copyrighted rulebook text is used — only the generic d20 math.
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
from app.rulesets.dnd5e.prompts import build_gm_system
from app.rulesets.dnd5e.schema import (
    ABILITIES,
    ABILITY_NAMES,
    SKILL_ABILITY,
    DnD5eCharacterData,
    DnD5eRulesetConfig,
    ability_modifier,
    proficiency_bonus_for_level,
)

OUTCOME_LABELS = {
    "critical_success": "Critical Success",
    "success": "Success",
    "partial": "Partial Success",
    "failure": "Failure",
    "critical_failure": "Critical Failure",
    "none": "No Check",
}

_NO_CHECK_ACTIONS = {"move", "talk", "examine", "other"}
_CHECK_ACTIONS = {"attack", "skill_check", "saving_throw", "cast_spell", "use_item"}


class DnD5eRuleset(BaseRuleset):
    id = "dnd5e"
    name = "D&D 5e (d20 System)"
    description = (
        "A d20 fantasy system adapter with ability scores, modifiers, proficiency, "
        "armor class, hit points, saving throws, and critical hits."
    )

    # ------------------------------------------------------------------ #
    # Config & character schema
    # ------------------------------------------------------------------ #
    def default_config(self) -> dict[str, Any]:
        return DnD5eRulesetConfig().model_dump()

    def character_schema(self) -> dict[str, Any]:
        return {
            "abilities": [
                {"key": k, "name": ABILITY_NAMES[k], "default": 10, "min": 1, "max": 30}
                for k in ABILITIES
            ],
            "skills": [{"name": s, "ability": a} for s, a in SKILL_ABILITY.items()],
            "fields": [
                {"key": "char_class", "label": "Class", "type": "string"},
                {"key": "level", "label": "Level", "type": "int"},
                {"key": "armor_class", "label": "Armor Class", "type": "int"},
                {"key": "hit_dice", "label": "Hit Dice", "type": "string"},
            ],
            "resources": [{"name": "HP", "abbreviation": "HP"}],
        }

    def new_character_data(self, config: dict[str, Any]) -> dict[str, Any]:
        cfg = DnD5eRulesetConfig(**(config or {}))
        level = cfg.starting_level
        data = DnD5eCharacterData(
            char_class="Fighter",
            level=level,
            proficiency_bonus=proficiency_bonus_for_level(level),
            abilities={k: cfg.default_ability_score for k in ABILITIES},
            proficient_skills=[],
            proficient_saves=["str", "con"],
            armor_class=cfg.default_ac,
            resources={"HP": {"current": cfg.default_hp, "max": cfg.default_hp}},
            hit_dice=f"{level}d10",
            spell_slots={},
        )
        return data.model_dump()

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
        if intent.action_type == "attack" and intent.target_id:
            target = state.get_character(intent.target_id)
            target_npc = next((n for n in state.npcs if n.id == intent.target_id), None)
            if target is None and target_npc is None:
                raise RuleViolationError("Attack target does not exist.")

    # ------------------------------------------------------------------ #
    # Resolution helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _abilities(actor) -> dict[str, int]:
        data = (actor.ruleset_data or {}) if actor else {}
        return data.get("abilities", {}) or {}

    @staticmethod
    def _prof_bonus(actor) -> int:
        data = (actor.ruleset_data or {}) if actor else {}
        if "proficiency_bonus" in data:
            return int(data["proficiency_bonus"])
        return proficiency_bonus_for_level(int(data.get("level", 1)))

    def _mod(self, actor, ability_key: str) -> int:
        score = self._abilities(actor).get(ability_key, 10)
        return ability_modifier(int(score))

    def _target_ac(self, intent: ActionIntent, state: GameState, config) -> int:
        if intent.target_id:
            target = state.get_character(intent.target_id)
            if target is not None:
                return int((target.ruleset_data or {}).get("armor_class", config.default_ac))
        if intent.metadata and "target_ac" in intent.metadata:
            return int(intent.metadata["target_ac"])
        return int(config.default_ac)

    @staticmethod
    def _build_roll_dict(notation: str, natural: int, modifier: int) -> dict[str, Any]:
        return {
            "notation": notation,
            "num_dice": 1,
            "sides": 20,
            "modifier": modifier,
            "rolls": [natural],
            "total": natural + modifier,
        }

    # ------------------------------------------------------------------ #
    # Resolution
    # ------------------------------------------------------------------ #
    def resolve_action(
        self, intent: ActionIntent, state: GameState, rng: random.Random | None = None
    ) -> ActionResult:
        config = DnD5eRulesetConfig(**(state.ruleset_config or {}))
        actor = (
            state.get_character(intent.actor_id)
            if intent.actor_id
            else state.get_player_character()
        )

        if intent.action_type in _NO_CHECK_ACTIONS:
            return self._resolve_no_check(intent, actor)

        if intent.action_type == "attack":
            return self._resolve_attack(intent, state, actor, config, rng)
        if intent.action_type == "saving_throw":
            return self._resolve_save(intent, actor, config, rng)
        # skill_check, cast_spell, use_item -> ability/skill check
        return self._resolve_skill_check(intent, actor, config, rng)

    def _resolve_no_check(self, intent: ActionIntent, actor) -> ActionResult:
        mutations: list[StateMutation] = []
        desc = "No roll required; narration resolves this action."
        if intent.action_type == "move" and intent.target_location_id and actor:
            mutations.append(
                MoveMutation(character_id=actor.id, to_location_id=intent.target_location_id)
            )
            desc = f"{actor.name} moves to a new location."
        return ActionResult(
            intent=intent,
            check_required=False,
            dice_rolled=None,
            outcome="none",
            outcome_label=OUTCOME_LABELS["none"],
            mechanical_description=desc,
            state_mutations=mutations,
        )

    def _resolve_attack(
        self, intent: ActionIntent, state: GameState, actor, config, rng
    ) -> ActionResult:
        ability_key = (intent.metadata or {}).get("attack_ability", "str")
        if ability_key not in ABILITIES:
            ability_key = "str"
        d20 = roll_dice("1d20", rng=rng)
        natural = d20.rolls[0]
        mod = self._mod(actor, ability_key) + self._prof_bonus(actor)
        total = natural + mod
        ac = self._target_ac(intent, state, config)
        name = actor.name if actor else "The attacker"

        is_crit = natural >= config.crit_on
        is_fumble = natural <= config.fumble_on

        if is_fumble:
            outcome = "critical_failure"
            hit = False
        elif is_crit:
            outcome = "critical_success"
            hit = True
        elif total >= ac:
            outcome = "success"
            hit = True
        else:
            outcome = "failure"
            hit = False

        mutations: list[StateMutation] = []
        damage_desc = ""
        if hit:
            damage_dice = (intent.metadata or {}).get("damage_dice", "1d6")
            dmg_mod = self._mod(actor, ability_key)
            dmg_roll = roll_dice(damage_dice, rng=rng)
            damage = dmg_roll.total
            if is_crit:
                # Critical hit: roll the damage dice a second time (double dice, not mod).
                extra = roll_dice(damage_dice, rng=rng)
                damage += sum(extra.rolls)
            damage = max(1, damage + dmg_mod)
            if intent.target_id:
                mutations.append(
                    DamageMutation(character_id=intent.target_id, resource="HP", amount=damage)
                )
            crit_note = " (critical hit — doubled damage dice)" if is_crit else ""
            damage_desc = f" dealing {damage} damage{crit_note}"

        notation = f"1d20{'+' if mod >= 0 else ''}{mod}"
        result = ActionResult(
            intent=intent,
            check_required=True,
            dice_rolled=self._build_roll_dict(notation, natural, mod),
            outcome=outcome,
            outcome_label=OUTCOME_LABELS[outcome],
        )
        if is_fumble:
            result.mechanical_description = f"{name} fumbles the attack (natural 1)."
        elif hit:
            result.mechanical_description = (
                f"{name} hits (rolled {total} vs AC {ac}){damage_desc}."
            )
        else:
            result.mechanical_description = f"{name} misses (rolled {total} vs AC {ac})."
        result.state_mutations = mutations
        return result

    def _resolve_skill_check(self, intent: ActionIntent, actor, config, rng) -> ActionResult:
        skill = intent.skill_used or ""
        ability_key = SKILL_ABILITY.get(skill)
        if ability_key is None:
            ability_key = (intent.metadata or {}).get("ability", "wis")
        if ability_key not in ABILITIES:
            ability_key = "wis"
        proficient = actor is not None and skill in (
            (actor.ruleset_data or {}).get("proficient_skills", [])
        )
        d20 = roll_dice("1d20", rng=rng)
        natural = d20.rolls[0]
        mod = self._mod(actor, ability_key)
        if proficient:
            mod += self._prof_bonus(actor)
        total = natural + mod
        dc = int((intent.metadata or {}).get("dc", 15))
        name = actor.name if actor else "The character"

        if natural >= config.crit_on:
            outcome = "critical_success"
        elif natural <= config.fumble_on:
            outcome = "critical_failure"
        elif total >= dc:
            outcome = "success"
        elif total >= dc - 3:
            outcome = "partial"
        else:
            outcome = "failure"

        notation = f"1d20{'+' if mod >= 0 else ''}{mod}"
        label = ABILITY_NAMES.get(ability_key, ability_key.upper())
        check_name = skill or label
        result = ActionResult(
            intent=intent,
            check_required=True,
            dice_rolled=self._build_roll_dict(notation, natural, mod),
            outcome=outcome,
            outcome_label=OUTCOME_LABELS[outcome],
        )
        result.mechanical_description = (
            f"{name} attempts a {check_name} check — rolled {total} vs DC {dc} "
            f"({OUTCOME_LABELS[outcome]})."
        )
        return result

    def _resolve_save(self, intent: ActionIntent, actor, config, rng) -> ActionResult:
        ability_key = (intent.metadata or {}).get("ability", intent.skill_used or "con")
        if ability_key not in ABILITIES:
            ability_key = "con"
        proficient = actor is not None and ability_key in (
            (actor.ruleset_data or {}).get("proficient_saves", [])
        )
        d20 = roll_dice("1d20", rng=rng)
        natural = d20.rolls[0]
        mod = self._mod(actor, ability_key)
        if proficient:
            mod += self._prof_bonus(actor)
        total = natural + mod
        dc = int((intent.metadata or {}).get("dc", 13))
        name = actor.name if actor else "The character"

        if natural <= config.fumble_on:
            outcome = "critical_failure"
        elif natural >= config.crit_on:
            outcome = "critical_success"
        elif total >= dc:
            outcome = "success"
        else:
            outcome = "failure"

        notation = f"1d20{'+' if mod >= 0 else ''}{mod}"
        result = ActionResult(
            intent=intent,
            check_required=True,
            dice_rolled=self._build_roll_dict(notation, natural, mod),
            outcome=outcome,
            outcome_label=OUTCOME_LABELS[outcome],
        )
        result.mechanical_description = (
            f"{name} makes a {ABILITY_NAMES.get(ability_key, ability_key)} saving throw — "
            f"rolled {total} vs DC {dc} ({OUTCOME_LABELS[outcome]})."
        )
        return result

    # ------------------------------------------------------------------ #
    # Initiative & prompt
    # ------------------------------------------------------------------ #
    def get_initiative(self, character_data: dict[str, Any]) -> int:
        abilities = (character_data or {}).get("abilities", {})
        dex = int(abilities.get("dex", 10))
        return 10 + ability_modifier(dex)

    def system_prompt_fragment(self, state: GameState) -> str:
        return build_gm_system(state.ruleset_config or {}, dict(state.gm_config or {}))
