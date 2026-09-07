"""Turns raw player text into a structured ActionIntent via an AI JSON call.

Includes a deterministic heuristic fallback so the pipeline works even without
a perfect AI response (and is used when the AI returns malformed data).
"""
from __future__ import annotations

from app.ai.provider_base import AIProvider
from app.game.rules.base_ruleset import ActionIntent
from app.game.state.game_state import GameState
from app.rulesets.generic.prompts import INTENT_PARSER_SYSTEM

_ACTION_TYPES = {"attack", "skill_check", "move", "talk", "examine", "use_item", "other"}

_KEYWORDS = {
    "attack": ["attack", "hit", "strike", "stab", "shoot", "fight", "swing", "punch", "kill"],
    "move": ["go", "walk", "run", "move", "travel", "enter", "leave", "head", "climb"],
    "talk": ["say", "talk", "ask", "tell", "speak", "greet", "persuade", "convince", "shout"],
    "examine": ["look", "examine", "inspect", "search", "study", "read", "observe"],
    "use_item": ["use", "drink", "eat", "throw", "cast", "apply", "equip"],
}


def _build_context(state: GameState) -> str:
    lines = []
    pc = state.get_player_character()
    if pc:
        lines.append(f"Player character: id={pc.id} name={pc.name}")
    loc = state.get_location(state.current_location_id)
    if loc:
        lines.append(f"Current location: id={loc.id} name={loc.name}")
    for n in state.npcs_in_location(state.current_location_id):
        lines.append(f"NPC present: id={n.id} name={n.name}")
    for l in state.locations:
        lines.append(f"Location: id={l.id} name={l.name}")
    return "\n".join(lines) if lines else "(no context)"


def heuristic_intent(text: str, state: GameState) -> ActionIntent:
    lowered = text.lower()
    action_type = "other"
    for atype, words in _KEYWORDS.items():
        if any(w in lowered for w in words):
            action_type = "skill_check" if atype == "use_item" and "use" not in lowered else atype
            action_type = atype
            break
    pc = state.get_player_character()
    intent = ActionIntent(
        action_type=action_type,
        description=text.strip()[:200],
        actor_id=pc.id if pc else None,
        raw_text=text,
    )
    # Try to match a target NPC by name.
    for n in state.npcs_in_location(state.current_location_id):
        if n.name.lower() in lowered:
            intent.target_id = n.id
            break
    # Try to match destination location by name for movement.
    if action_type == "move":
        for l in state.locations:
            if l.name.lower() in lowered and l.id != state.current_location_id:
                intent.target_location_id = l.id
                break
    return intent


class IntentParser:
    def __init__(self, provider: AIProvider | None) -> None:
        self.provider = provider

    async def parse(self, text: str, state: GameState) -> ActionIntent:
        # Always compute a heuristic baseline.
        baseline = heuristic_intent(text, state)
        if self.provider is None:
            return baseline
        system = INTENT_PARSER_SYSTEM.format(context=_build_context(state))
        try:
            data = await self.provider.complete_json(system, text)
        except Exception:  # noqa: BLE001 - fall back to heuristic
            return baseline
        if not isinstance(data, dict) or not data:
            return baseline

        action_type = data.get("action_type")
        if action_type not in _ACTION_TYPES:
            action_type = baseline.action_type
        pc = state.get_player_character()
        return ActionIntent(
            action_type=action_type,
            description=data.get("description") or baseline.description,
            actor_id=baseline.actor_id or (pc.id if pc else None),
            skill_used=data.get("skill_used") or None,
            target_id=data.get("target_id") or baseline.target_id,
            target_location_id=data.get("target_location_id") or baseline.target_location_id,
            raw_text=text,
        )
