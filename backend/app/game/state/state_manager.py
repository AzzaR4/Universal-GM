"""Loads GameState from the database and applies typed mutations back to it.

This is the ONLY component that writes game-state changes to the DB as a result
of gameplay. Mutations come exclusively from the Rules Engine.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, RuleViolationError
from app.db.models import Campaign, Character, Location, NPC, Quest
from app.game.state.combat_state import Combatant, CombatState
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

    # ------------------------------------------------------------------ #
    # Combat management
    # ------------------------------------------------------------------ #
    @staticmethod
    def _primary_resource(ruleset_data: dict) -> tuple[str, dict]:
        """Return (resource_name, {current,max}) for a character's health pool."""
        resources = (ruleset_data or {}).get("resources", {}) or {}
        for key in ("HP", "Health", "Endurance"):
            if key in resources:
                return key, resources[key]
        if resources:
            name = next(iter(resources))
            return name, resources[name]
        return "HP", {"current": 10, "max": 10}

    async def get_combat(self, campaign_id: str) -> CombatState | None:
        campaign = await self.session.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        return CombatState.from_dict(campaign.active_combat)

    async def start_combat(
        self,
        campaign_id: str,
        enemy_ids: list[str] | None = None,
        default_enemy_hp: int = 10,
    ) -> CombatState:
        """Begin a combat encounter with all living player characters plus the
        selected NPCs (or every NPC in the party's current location)."""
        from app.rulesets.registry import get_ruleset

        campaign = await self.session.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        ruleset = get_ruleset(campaign.ruleset_id)

        chars = (
            await self.session.execute(
                select(Character).where(Character.campaign_id == campaign_id)
            )
        ).scalars().all()
        npcs = (
            await self.session.execute(select(NPC).where(NPC.campaign_id == campaign_id))
        ).scalars().all()

        combatants: list[Combatant] = []
        for c in chars:
            if c.status != "alive":
                continue
            res_name, res = self._primary_resource(c.ruleset_data or {})
            combatants.append(
                Combatant(
                    id=c.id,
                    name=c.name,
                    is_player=c.is_player_character,
                    initiative=ruleset.get_initiative(c.ruleset_data or {}),
                    hp_current=int(res.get("current", 0)),
                    hp_max=int(res.get("max", 0)),
                    resource=res_name,
                    status="alive",
                    is_npc=False,
                )
            )

        # Enemy selection.
        if enemy_ids is not None:
            selected = [n for n in npcs if n.id in set(enemy_ids)]
        else:
            loc = campaign.current_location_id
            selected = [
                n for n in npcs if n.status == "alive" and (not loc or n.location_id == loc)
            ]
        for n in selected:
            combatants.append(
                Combatant(
                    id=n.id,
                    name=n.name,
                    is_player=False,
                    initiative=ruleset.get_initiative({}),
                    hp_current=default_enemy_hp,
                    hp_max=default_enemy_hp,
                    resource="HP",
                    status="alive",
                    is_npc=True,
                )
            )

        combat = CombatState(active=True, round=1, turn_index=0, combatants=combatants)
        first = combat.current_combatant()
        combat.log.append(
            f"Combat begins! {first.name} acts first." if first else "Combat begins!"
        )
        campaign.active_combat = combat.to_dict()
        await self.session.commit()
        return combat

    async def apply_combat_action(
        self,
        campaign_id: str,
        actor_id: str | None,
        target_id: str | None,
        damage: int = 0,
        note: str = "",
        end_turn: bool = True,
    ) -> CombatState:
        """Apply damage to a combatant, sync HP to the DB, advance the turn, and
        detect defeat / end-of-combat."""
        campaign = await self.session.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        combat = CombatState.from_dict(campaign.active_combat)
        if combat is None or not combat.active:
            raise RuleViolationError("No active combat for this campaign.")

        if target_id and damage:
            target = combat.get(target_id)
            if target is not None:
                target.hp_current = max(0, target.hp_current - int(damage))
                if target.hp_current <= 0 and target.status == "alive":
                    target.status = "defeated"
                    combat.log.append(f"{target.name} is defeated!")
                # Sync to the underlying character (NPC HP lives only in combat).
                if not target.is_npc:
                    char = await self.session.get(Character, target.id)
                    if char is not None:
                        data = dict(char.ruleset_data or {})
                        resources = dict(data.get("resources", {}))
                        res = dict(resources.get(target.resource, {"current": 0, "max": target.hp_max}))
                        res["current"] = target.hp_current
                        resources[target.resource] = res
                        data["resources"] = resources
                        char.ruleset_data = data
                        if target.hp_current <= 0:
                            char.status = "defeated"
                else:
                    npc = await self.session.get(NPC, target.id)
                    if npc is not None and target.hp_current <= 0:
                        npc.status = "defeated"

        if note:
            combat.log.append(note)

        if end_turn and not combat.is_over():
            combat.advance_turn()
            nxt = combat.current_combatant()
            if nxt:
                combat.log.append(f"It is now {nxt.name}'s turn (round {combat.round}).")

        if combat.is_over():
            combat.active = False
            combat.log.append("The combat has ended.")

        campaign.active_combat = combat.to_dict()
        await self.session.commit()
        return combat

    async def end_combat(self, campaign_id: str) -> None:
        campaign = await self.session.get(Campaign, campaign_id)
        if campaign is None:
            raise NotFoundError(f"Campaign {campaign_id} not found")
        campaign.active_combat = None
        await self.session.commit()
