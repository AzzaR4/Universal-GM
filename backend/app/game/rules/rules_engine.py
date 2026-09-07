"""Orchestrates ruleset calls. Stateless. Never touches the AI or the DB."""
from __future__ import annotations

from app.game.rules.base_ruleset import ActionIntent, ActionResult
from app.game.state.game_state import GameState
from app.rulesets.registry import get_ruleset


class RulesEngine:
    """Thin orchestrator that delegates to the campaign's ruleset."""

    def resolve(self, intent: ActionIntent, state: GameState) -> ActionResult:
        ruleset = get_ruleset(state.ruleset_id)
        # Validation raises RuleViolationError on illegal actions.
        ruleset.validate_action(intent, state)
        return ruleset.resolve_action(intent, state)

    def system_prompt_fragment(self, state: GameState) -> str:
        ruleset = get_ruleset(state.ruleset_id)
        return ruleset.system_prompt_fragment(state)


rules_engine = RulesEngine()
