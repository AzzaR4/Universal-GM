"""The Narrative Engine orchestrates the full player-action pipeline.

Pipeline (per POST /api/campaigns/{id}/actions):
  1. Load authoritative GameState
  2. Parse intent (AI JSON, with heuristic fallback)   -> emit "intent"
  3. Resolve via Rules Engine (NO AI)                    -> emit "dice"
  4. Apply typed state mutations to the DB
  5. Emit + log domain events
  6. Stream narration (the creative AI call)             -> emit "narrative" chunks
  7. Persist narration to memory + event log             -> emit "complete"

Everything is yielded as SSE-friendly dict events. Graceful degradation: if the
AI provider is unavailable, a mechanical fallback narration is produced so the
game remains playable.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider_registry import get_active_provider
from app.core.events import event_bus
from app.core.exceptions import AIProviderError, DomainError
from app.db.models import EventLog
from app.game.memory.memory_manager import MemoryManager
from app.game.narrative.intent_parser import IntentParser
from app.game.narrative.narrator import Narrator
from app.game.narrative.prompt_builder import build_narration_prompt
from app.game.rules.rules_engine import rules_engine
from app.game.state.state_manager import StateManager


class NarrativeEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.state_manager = StateManager(session)
        self.memory = MemoryManager(session)

    async def run_action(
        self, campaign_id: str, action_text: str
    ) -> AsyncIterator[dict[str, Any]]:
        # ---- Load state ----
        try:
            state = await self.state_manager.load(campaign_id)
        except DomainError as exc:
            yield {"type": "error", "data": str(exc)}
            return

        # ---- Acquire AI provider (optional; degrade gracefully) ----
        provider = None
        provider_error: str | None = None
        try:
            provider = await get_active_provider(self.session)
        except AIProviderError as exc:
            provider_error = str(exc)

        # ---- Parse intent ----
        parser = IntentParser(provider)
        try:
            intent = await parser.parse(action_text, state)
        except Exception as exc:  # noqa: BLE001
            yield {"type": "error", "data": f"Intent parsing failed: {exc}"}
            return
        yield {"type": "intent", "data": intent.to_dict()}

        # ---- Resolve via Rules Engine ----
        try:
            result = rules_engine.resolve(intent, state)
        except DomainError as exc:
            yield {"type": "error", "data": str(exc)}
            return
        if result.check_required and result.dice_rolled:
            yield {
                "type": "dice",
                "data": {
                    "roll": result.dice_rolled,
                    "outcome": result.outcome,
                    "outcome_label": result.outcome_label,
                },
            }

        # ---- Apply mutations ----
        applied = await self.state_manager.apply_mutations(campaign_id, result.state_mutations)

        # ---- Log domain events ----
        await self._log_event(campaign_id, "action_attempted", {
            "intent": intent.to_dict(),
            "summary": f"Player: {action_text[:120]}",
        })
        await self._log_event(campaign_id, "check_resolved", {
            "outcome": result.outcome,
            "dice": result.dice_rolled,
            "mutations": applied,
        })
        await event_bus.publish(
            type("Ev", (), {"event_type": "check_resolved", "campaign_id": campaign_id})()
        )

        # ---- Narration ----
        short_term = await self.memory.short_term(campaign_id)
        relevant = await self.memory.retrieve_relevant(campaign_id, action_text)
        system, user = build_narration_prompt(state, result, short_term, relevant)

        full_text = ""
        if provider is not None:
            narrator = Narrator(provider)
            try:
                async for chunk in narrator.narrate(system, user):
                    full_text += chunk
                    yield {"type": "narrative", "data": chunk}
            except AIProviderError as exc:
                fallback = self._fallback_narration(result, provider_error or str(exc))
                full_text = fallback
                yield {"type": "narrative", "data": fallback}
        else:
            fallback = self._fallback_narration(result, provider_error)
            full_text = fallback
            yield {"type": "narrative", "data": fallback}

        # ---- Persist narration ----
        await self._log_event(campaign_id, "narration_generated", {
            "narration": full_text,
            "summary": full_text[:200],
        })
        importance = 0.8 if result.outcome in {"critical_success", "critical_failure"} else 0.5
        await self.memory.record(
            campaign_id, full_text, memory_type="narration", importance=importance
        )
        await self.session.commit()

        # ---- Complete ----
        yield {
            "type": "complete",
            "data": {
                "outcome": result.outcome,
                "outcome_label": result.outcome_label,
                "mutations": applied,
                "narration": full_text,
                "ai_available": provider is not None,
            },
        }

    async def _log_event(self, campaign_id: str, event_type: str, data: dict) -> None:
        self.session.add(
            EventLog(campaign_id=campaign_id, event_type=event_type, data=data)
        )
        await self.session.flush()

    @staticmethod
    def _fallback_narration(result, provider_error: str | None) -> str:
        base = result.mechanical_description or "The action resolves."
        note = (
            " (AI narration unavailable — showing the mechanical result. "
            "Configure an AI provider in Settings for full storytelling.)"
        )
        if provider_error:
            return f"[{result.outcome_label}] {base}{note}"
        return f"[{result.outcome_label}] {base}{note}"
