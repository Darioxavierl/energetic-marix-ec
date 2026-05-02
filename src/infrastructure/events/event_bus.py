"""Minimal synchronous event bus for in-process decoupling."""

from collections import defaultdict
from collections.abc import Callable


class EventBus:
    """Lightweight pub/sub implementation for UI and app layers."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable[[dict], None]]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Callable[[dict], None]) -> None:
        """Register event handler for a specific event key."""

        self._subscribers[event_name].append(handler)

    def publish(self, event_name: str, payload: dict | None = None) -> None:
        """Dispatch payload to all handlers subscribed to an event."""

        data = payload or {}
        for handler in self._subscribers.get(event_name, []):
            handler(data)
