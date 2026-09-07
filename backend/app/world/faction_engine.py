"""Faction autonomy engine.

Factions act autonomously; the world changes whether or not the players engage.
The engine is driven either after player actions (a lightweight check) or via an
explicit ``/world/tick`` API call.

Design notes:
- If an AI provider is configured, the faction "decides" its next action via a
  JSON-mode completion. If no provider is available (e.g. during tests or a
  self-hosted install without AI configured) the engine degrades gracefully to a
  deterministic, goal-driven action so the simulation always progresses.
- Autonomy thresholds are expressed in *player actions since the faction last
  acted*: passive never acts, active acts every 5 actions, aggressive every 2.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AIProviderError
from app.db.models import EventLog, Faction, WorldEvent

# Player actions required before a faction of each autonomy level acts.
AUTONOMY_THRESHOLDS: dict[str, int | None] = {
    "passive": None,   # never acts autonomously
    "active": 5,
    "aggressive": 2,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


class FactionEngine:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def tick(self, campaign_id: str, force: bool = False) -> list[WorldEvent]:
        """Run one autonomy cycle for a campaign.

        Returns the list of newly created ``WorldEvent`` rows. When ``force`` is
        True every non-passive faction acts regardless of its threshold (used by
        the manual "Tick World" button).
        """
        factions = (
            await self.session.execute(
                select(Faction).where(Faction.campaign_id == campaign_id)
            )
        ).scalars().all()

        created: list[WorldEvent] = []
        for faction in factions:
            if faction.autonomy_level == "passive":
                continue
            threshold = AUTONOMY_THRESHOLDS.get(faction.autonomy_level)
            if threshold is None:
                continue
            actions_since = await self._actions_since(campaign_id, faction.last_acted_at)
            if not force and actions_since < threshold:
                continue
            event = await self._act(campaign_id, faction)
            created.append(event)
        if created:
            await self.session.commit()
            for e in created:
                await self.session.refresh(e)
        return created

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    async def _actions_since(self, campaign_id: str, since: datetime | None) -> int:
        stmt = select(EventLog).where(
            EventLog.campaign_id == campaign_id,
            EventLog.event_type == "action",
        )
        if since is not None:
            stmt = stmt.where(EventLog.timestamp > since)
        rows = (await self.session.execute(stmt)).scalars().all()
        return len(rows)

    async def _act(self, campaign_id: str, faction: Faction) -> WorldEvent:
        action = await self._decide_action(faction)
        impact = action.get("impact") or {}
        event = WorldEvent(
            campaign_id=campaign_id,
            faction_id=faction.id,
            event_type=action.get("event_type", "faction_action"),
            title=action.get("title", f"{faction.name} makes a move"),
            description=action.get("description", ""),
            impact=impact,
            is_revealed=False,
        )
        self.session.add(event)
        self._apply_impact(faction, impact)
        faction.last_acted_at = _now()
        return event

    async def _decide_action(self, faction: Faction) -> dict:
        """Ask the AI to decide the faction's next action; fall back if unavailable."""
        try:
            # Imported lazily so the engine has no hard dependency on AI wiring.
            from app.ai.provider_registry import get_active_provider

            provider = await get_active_provider(self.session)
            system, user = self.build_faction_prompt(faction)
            data = await provider.complete_json(system, user)
            if isinstance(data, dict) and (data.get("title") or data.get("description")):
                return self._normalise_action(data)
        except AIProviderError:
            pass
        except Exception:  # noqa: BLE001 - any AI failure degrades gracefully
            pass
        return self._fallback_action(faction)

    @staticmethod
    def _normalise_action(data: dict) -> dict:
        impact = data.get("impact") or {}
        if not isinstance(impact, dict):
            impact = {}
        return {
            "event_type": str(data.get("event_type", "faction_action")),
            "title": str(data.get("title", "")).strip() or "Faction action",
            "description": str(data.get("description", "")).strip(),
            "impact": {
                "resources_delta": int(impact.get("resources_delta", 0) or 0),
                "influence_delta": int(impact.get("influence_delta", 0) or 0),
                "affected_factions": impact.get("affected_factions", []) or [],
            },
        }

    def _fallback_action(self, faction: Faction) -> dict:
        """Deterministic goal-driven action used when no AI provider is active."""
        goal = ""
        if faction.goals:
            goal = str(faction.goals[0])
        disp = faction.disposition
        if disp == "hostile":
            title = f"{faction.name} escalates its campaign"
            desc = (
                f"{faction.name} moves aggressively"
                + (f" to {goal}" if goal else "")
                + ", spending resources to expand its influence."
            )
            impact = {"resources_delta": -5, "influence_delta": 8, "affected_factions": []}
        elif disp == "friendly":
            title = f"{faction.name} consolidates alliances"
            desc = (
                f"{faction.name} works quietly"
                + (f" toward {goal}" if goal else "")
                + ", trading favors to shore up its standing."
            )
            impact = {"resources_delta": 4, "influence_delta": 3, "affected_factions": []}
        else:
            title = f"{faction.name} advances its agenda"
            desc = (
                f"{faction.name} makes a measured move"
                + (f" to {goal}" if goal else "")
                + "."
            )
            impact = {"resources_delta": 2, "influence_delta": 2, "affected_factions": []}
        return {
            "event_type": "faction_action",
            "title": title,
            "description": desc,
            "impact": impact,
        }

    def _apply_impact(self, faction: Faction, impact: dict) -> None:
        if not isinstance(impact, dict):
            return
        faction.resources = _clamp(
            faction.resources + int(impact.get("resources_delta", 0) or 0)
        )
        faction.influence = _clamp(
            faction.influence + int(impact.get("influence_delta", 0) or 0)
        )

    # ------------------------------------------------------------------ #
    # Prompt building (exposed for tests / reuse)
    # ------------------------------------------------------------------ #
    def build_faction_prompt(self, faction: Faction) -> tuple[str, str]:
        system = (
            "You are the world simulation engine for a tabletop RPG. You control a "
            "faction that acts autonomously between player scenes. Decide the single "
            "most plausible next action this faction takes to pursue its goals. "
            "Respond with ONLY a JSON object with keys: event_type (string), title "
            "(string), description (2-3 sentences), and impact (object with integer "
            "resources_delta, integer influence_delta, and array affected_factions)."
        )
        goals = ", ".join(str(g) for g in (faction.goals or [])) or "(none stated)"
        rels = json.dumps(faction.relationships or {})
        user = (
            f"Faction: {faction.name}\n"
            f"Description: {faction.description}\n"
            f"Goals: {goals}\n"
            f"Disposition toward the party: {faction.disposition}\n"
            f"Resources (0-100): {faction.resources}\n"
            f"Influence (0-100): {faction.influence}\n"
            f"Relationships: {rels}\n"
            f"Autonomy level: {faction.autonomy_level}\n\n"
            "What does this faction do next?"
        )
        return system, user
