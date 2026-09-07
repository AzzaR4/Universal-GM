"""A lightweight async publish/subscribe event bus.

This is the in-process event bus. Domain events (see app.game.events.types) are
published here; subscribers (loggers, memory formation, UI streamers) react.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

Handler = Callable[[Any], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._wildcard: list[Handler] = []

    def subscribe(self, event_type: str, handler: Handler) -> None:
        if event_type == "*":
            self._wildcard.append(handler)
        else:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        if event_type == "*":
            if handler in self._wildcard:
                self._wildcard.remove(handler)
        elif handler in self._subscribers.get(event_type, []):
            self._subscribers[event_type].remove(handler)

    async def publish(self, event: Any) -> None:
        event_type = getattr(event, "event_type", None) or type(event).__name__
        handlers = list(self._subscribers.get(event_type, [])) + list(self._wildcard)
        if not handlers:
            return
        await asyncio.gather(*(h(event) for h in handlers), return_exceptions=True)


# Application-wide singleton bus.
event_bus = EventBus()
