"""Tests for lightweight event bus."""

from src.infrastructure.events.event_bus import EventBus


def test_event_bus_publish_dispatches_payload():
    bus = EventBus()
    calls = []

    def handler(payload: dict):
        calls.append(payload)

    bus.subscribe("state_updated", handler)
    bus.publish("state_updated", {"value": 42})

    assert len(calls) == 1
    assert calls[0]["value"] == 42


def test_event_bus_ignores_unknown_event():
    bus = EventBus()
    # Should not raise
    bus.publish("unknown", {"noop": True})
