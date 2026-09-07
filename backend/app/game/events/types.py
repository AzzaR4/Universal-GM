"""Domain event definitions.

Events are immutable facts about things that happened in the game. They are
published to the EventBus and logged to the EventLog table.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DomainEvent:
    event_type: str = "domain_event"
    campaign_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActionAttempted(DomainEvent):
    event_type: str = "action_attempted"


@dataclass
class CheckResolved(DomainEvent):
    event_type: str = "check_resolved"


@dataclass
class StateMutated(DomainEvent):
    event_type: str = "state_mutated"


@dataclass
class CharacterDamaged(DomainEvent):
    event_type: str = "character_damaged"


@dataclass
class CharacterMoved(DomainEvent):
    event_type: str = "character_moved"


@dataclass
class NarrationGenerated(DomainEvent):
    event_type: str = "narration_generated"


def make_event(event_type: str, campaign_id: str, data: dict[str, Any]) -> DomainEvent:
    return DomainEvent(event_type=event_type, campaign_id=campaign_id, data=data)
