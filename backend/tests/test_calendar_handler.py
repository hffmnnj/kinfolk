"""Tests for voice-driven calendar CRUD intent handler."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.calendar_event import CalendarEvent
from app.schemas.intent import Intent, IntentSlot
from app.services.calendar_sync import CalendarSyncService
from app.services.intent_handlers.calendar_handler import (
    CalendarIntentHandler,
    _format_event_time,
    _parse_datetime_nearest_future,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_sync_service(events: list[CalendarEvent] | None = None):
    """Build a CalendarSyncService with mocked internals."""
    svc = CalendarSyncService()
    svc._cached_events = list(events or [])
    svc.push_event = AsyncMock(
        side_effect=lambda e: e,
    )
    return svc


def _intent(name: str, slots: dict[str, str] | None = None) -> Intent:
    """Shorthand intent builder."""
    slot_list = [IntentSlot(name=k, value=v) for k, v in (slots or {}).items()]
    return Intent(name=name, slots=slot_list, confidence=0.95)


# ---------------------------------------------------------------------------
# Date/time parsing
# ---------------------------------------------------------------------------


class TestParseDatetimeNearestFuture:
    """Verify natural-language date parsing with nearest-future rule."""

    def test_tomorrow_at_2pm(self):
        ref = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        result = _parse_datetime_nearest_future(
            "tomorrow at 2pm",
            reference=ref,
        )
        assert result is not None
        assert result.day == 5
        assert result.hour == 14

    def test_next_friday(self):
        # Wednesday reference
        ref = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        result = _parse_datetime_nearest_future(
            "friday",
            reference=ref,
        )
        assert result is not None
        assert result.weekday() == 4  # Friday

    def test_today_at_3pm_future(self):
        ref = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        result = _parse_datetime_nearest_future(
            "3pm",
            reference=ref,
        )
        assert result is not None
        assert result.hour == 15

    def test_ambiguous_past_time_bumps_forward(self):
        ref = datetime(2026, 3, 4, 16, 0, tzinfo=timezone.utc)
        result = _parse_datetime_nearest_future(
            "2pm",
            reference=ref,
        )
        assert result is not None
        # 2pm today is past 4pm ref → should bump to next day
        assert result > ref

    def test_empty_string_returns_none(self):
        ref = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        assert _parse_datetime_nearest_future("", reference=ref) is None

    def test_unparseable_returns_none(self):
        ref = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        assert (
            _parse_datetime_nearest_future(
                "xyzzy gibberish",
                reference=ref,
            )
            is None
        )


# ---------------------------------------------------------------------------
# Add event
# ---------------------------------------------------------------------------


class TestHandleAddEvent:
    """Test creating events via voice."""

    @pytest.mark.asyncio
    async def test_add_event_with_title_and_time(self):
        sync = _make_sync_service()
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        now = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        with patch(
            "app.services.intent_handlers.calendar_handler.datetime",
        ) as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            intent = _intent(
                "add_calendar_event",
                {
                    "event": "dentist appointment",
                    "when": "tomorrow at 2pm",
                },
            )
            response = await handler.handle(intent)

        sync.push_event.assert_awaited_once()
        pushed: CalendarEvent = sync.push_event.call_args[0][0]
        assert pushed.title == "dentist appointment"
        assert "dentist appointment" in response
        assert "added" in response.lower()

    @pytest.mark.asyncio
    async def test_add_event_missing_title(self):
        sync = _make_sync_service()
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        intent = _intent("add_calendar_event", {"when": "tomorrow"})
        response = await handler.handle(intent)

        sync.push_event.assert_not_awaited()
        assert "need" in response.lower()

    @pytest.mark.asyncio
    async def test_add_event_no_time_defaults_to_one_hour(self):
        sync = _make_sync_service()
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        intent = _intent(
            "add_calendar_event",
            {
                "event": "team standup",
            },
        )
        response = await handler.handle(intent)

        sync.push_event.assert_awaited_once()
        assert "team standup" in response


# ---------------------------------------------------------------------------
# Query events
# ---------------------------------------------------------------------------


class TestHandleGetEvents:
    """Test querying calendar events via voice."""

    @pytest.mark.asyncio
    async def test_query_today_returns_spoken_list(self):
        now = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        events = [
            CalendarEvent(
                title="Team standup",
                start_time=now.replace(hour=9),
                end_time=now.replace(hour=9, minute=30),
            ),
            CalendarEvent(
                title="Lunch with Sarah",
                start_time=now.replace(hour=12),
                end_time=now.replace(hour=13),
            ),
        ]
        sync = _make_sync_service(events)
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        intent = _intent("get_calendar")
        response = await handler.handle(intent)

        assert "2 events" in response
        assert "Team standup" in response
        assert "Lunch with Sarah" in response

    @pytest.mark.asyncio
    async def test_query_no_events_returns_friendly_message(self):
        sync = _make_sync_service([])
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        intent = _intent("get_calendar")
        response = await handler.handle(intent)

        assert "no events" in response.lower()

    @pytest.mark.asyncio
    async def test_query_single_event_uses_singular(self):
        now = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        events = [
            CalendarEvent(
                title="Doctor visit",
                start_time=now.replace(hour=14),
                end_time=now.replace(hour=15),
            ),
        ]
        sync = _make_sync_service(events)
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        intent = _intent("get_calendar")
        response = await handler.handle(intent)

        assert "1 event" in response
        assert "Doctor visit" in response


# ---------------------------------------------------------------------------
# Delete event
# ---------------------------------------------------------------------------


class TestHandleDeleteEvent:
    """Test cancelling events via voice."""

    @pytest.mark.asyncio
    async def test_delete_matching_event(self):
        now = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        meeting = CalendarEvent(
            title="3pm meeting",
            start_time=now.replace(hour=15),
            end_time=now.replace(hour=16),
        )
        sync = _make_sync_service([meeting])
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        intent = _intent(
            "cancel_calendar_event",
            {
                "event": "3pm meeting",
            },
        )
        response = await handler.handle(intent)

        assert "cancelled" in response.lower()
        assert "3pm meeting" in response
        assert len(sync._cached_events) == 0

    @pytest.mark.asyncio
    async def test_delete_no_match_returns_not_found(self):
        now = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        events = [
            CalendarEvent(
                title="Team standup",
                start_time=now.replace(hour=9),
                end_time=now.replace(hour=10),
            ),
        ]
        sync = _make_sync_service(events)
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        intent = _intent(
            "cancel_calendar_event",
            {
                "event": "nonexistent event",
            },
        )
        response = await handler.handle(intent)

        assert "couldn't find" in response.lower()
        assert len(sync._cached_events) == 1

    @pytest.mark.asyncio
    async def test_delete_missing_event_slot(self):
        sync = _make_sync_service([])
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        intent = _intent("cancel_calendar_event")
        response = await handler.handle(intent)

        assert "which event" in response.lower()

    @pytest.mark.asyncio
    async def test_delete_partial_title_match(self):
        now = datetime(2026, 3, 4, 10, 0, tzinfo=timezone.utc)
        meeting = CalendarEvent(
            title="dentist appointment",
            start_time=now.replace(hour=14),
            end_time=now.replace(hour=15),
        )
        sync = _make_sync_service([meeting])
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        intent = _intent(
            "cancel_calendar_event",
            {
                "event": "dentist",
            },
        )
        response = await handler.handle(intent)

        assert "cancelled" in response.lower()
        assert "dentist appointment" in response


# ---------------------------------------------------------------------------
# Unknown calendar intent
# ---------------------------------------------------------------------------


class TestUnknownCalendarIntent:
    """Graceful handling of unrecognized calendar sub-intents."""

    @pytest.mark.asyncio
    async def test_unknown_calendar_intent(self):
        sync = _make_sync_service()
        handler = CalendarIntentHandler(calendar_sync_service=sync)

        intent = _intent("some_unknown_calendar_thing")
        response = await handler.handle(intent)

        assert "not sure" in response.lower()


# ---------------------------------------------------------------------------
# Format helpers
# ---------------------------------------------------------------------------


class TestFormatEventTime:
    """Verify TTS-friendly time formatting."""

    def test_today_label(self):
        now = datetime.now(timezone.utc)
        dt = now.replace(hour=14, minute=30)
        result = _format_event_time(dt)
        assert "today" in result

    def test_tomorrow_label(self):
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        dt = tomorrow.replace(hour=9, minute=0)
        result = _format_event_time(dt)
        assert "tomorrow" in result
