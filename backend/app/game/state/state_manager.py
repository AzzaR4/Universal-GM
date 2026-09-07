"""Loads GameState from the database and applies typed mutations back to it.

This is the ONLY component that writes game-state changes to the DB as a result
of gameplay. Mutations come exclusively from the Rules Engine.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.db.models import Campaign, Character, Location, NPC, Quest
from app.game.state.game_state import (
    AddConditionMutation,
    AddInventoryMutation,
    CharacterView,
    DamageMutation,
    GameState,
    HealMutation,
    LocationView,
    MoveMutation,
    NPCView,
    QuestView,
    RemoveConditionMutation,
    SetStatusMutation,
    StateMutation,
)


class StateManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load(self, campaign_id: str) -> GameState:
        campaign = await self.session.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError(f"Campaign {campaign_id} not found")

        chars = (
            await self.session.execute(
                select(Character).where(Character.campaign_id == campaign_id)
            )
        ).scalars().all()
        npcs = (
            await self.session.execute(select(NPC).where(NPC.campaign_id == campaign_id))
        ).scalars().all()
        locs = (
            await self.session.execute(
                select(Location).where(Location.campaign_id == campaign_id)
            )
        ).scalars().all()
        quests = (
            await self.session.execute(
                select(Quest).where(Quest.campaign_id == campaign_id)
            )
        ).scalars().all()

        return GameState(
            campaign_id=campaign.id,
            campaign_name=campaign.name,
            ruleset_id=campaign.ruleset_id,
            ruleset_config=campaign.ruleset_config or {},
            gm_config=campaign.gm_config or {},
            current_location_id=campaign.current_location_id,
            characters=[
                CharacterView(
                    id=c.id,
                    name=c.name,
                    description=c.description,
                    is_player_character=c.is_player_character,
                    ruleset_data=c.ruleset_data or {},
                    conditions=list(c.conditions or []),
                    inventory=list(c.inventory or []),
                    location_id=c.location_id,
                    status=c.status,
                )
                for c in chars
            ],
            npcs=[
                NPCView(
                    id=n.id,
                    name=n.name,
                    description=n.description,
                    location_id=n.location_id,
                    current_activity=n.current_activity,
                    status=n.status,
                    personality=n.personality or {},
                )
                for n in npcs
            ],
            locations=[
                LocationView(
                    id=l.id, name=l.name, description=l.description, atmosphere=l.atmosphere
                )
                for l in locs
            ],
            quests=[QuestView(id=q.id, title=q.title, status=q.status) for q in quests],
        )

    async def apply_mutations(
        self, campaign_id: str, mutations: list[StateMutation]
    ) -> list[dict]:
        """Apply mutations to the DB and return a list of applied-change summaries."""
        applied: list[dict] = []
        for mut in mutations:
            summary = await self._apply_one(campaign_id, mut)
            if summary:
                applied.append(summary)
        await self.session.commit()
        return applied

    async def _apply_one(self, campaign_id: str, mut: StateMutation) -> dict | None:
        if isinstance(mut, (DamageMutation, HealMutation)):
            char = await self.session.get(Character, mut.character_id)
            if not char:
                return None
            data = dict(char.ruleset_data or {})
            resources = dict(data.get("resources", {}))
            res = dict(resources.get(mut.resource, {"current": 0, "max": 0}))
            delta = -mut.amount if isinstance(mut, DamageMutation) else mut.amount
            new_current = res.get("current", 0) + delta
            new_current = max(0, min(new_current, res.get("max", new_current)))
            res["current"] = new_current
            resources[mut.resource] = res
            data["resources"] = resources
            char.ruleset_data = data
            # Death check.
            if new_current <= 0 and isinstance(mut, DamageMutation):
                char.status = "defeated"
            return {
                "kind": mut.kind,
                "character_id": mut.character_id,
                "resource": mut.resource,
                "new_value": new_current,
                "status": char.status,
            }

        if isinstance(mut, MoveMutation):
            char = await self.session.get(Character, mut.character_id)
            if not char:
                return None
            char.location_id = mut.to_location_id
            campaign = await self.session.get(Campaign, campaign_id)
            if campaign and char.is_player_character:
                campaign.current_location_id = mut.to_location_id
            return {"kind": mut.kind, "character_id": mut.character_id, "to": mut.to_location_id}

        if isinstance(mut, AddConditionMutation):
            char = await self.session.get(Character, mut.character_id)
            if not char:
                return None
            conditions = list(char.conditions or [])
            if mut.condition not in conditions:
                conditions.append(mut.condition)
            char.conditions = conditions
            return {"kind": mut.kind, "character_id": mut.character_id, "condition": mut.condition}

        if isinstance(mut, RemoveConditionMutation):
            char = await self.session.get(Character, mut.character_id)
            if not char:
                return None
            conditions = [c for c in (char.conditions or []) if c != mut.condition]
            char.conditions = conditions
            return {"kind": mut.kind, "character_id": mut.character_id, "condition": mut.condition}

        if isinstance(mut, AddInventoryMutation):
            char = await self.session.get(Character, mut.character_id)
            if not char:
                return None
            inv = list(char.inventory or [])
            inv.append(mut.item)
            char.inventory = inv
            return {"kind": mut.kind, "character_id": mut.character_id, "item": mut.item}

        if isinstance(mut, SetStatusMutation):
            char = await self.session.get(Character, mut.character_id)
            if not char:
                return None
            char.status = mut.status
            return {"kind": mut.kind, "character_id": mut.character_id, "status": mut.status}

        return None
