"""Re-export of the application event bus for the game.events namespace."""
from __future__ import annotations

from app.core.events import EventBus, event_bus

__all__ = ["EventBus", "event_bus"]
