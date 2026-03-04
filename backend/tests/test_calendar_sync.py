"""Tests for the calendar sync scheduler service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.calendar_event import CalendarEvent
from app.services.calendar_sync import (
    CalendarSyncService,
    SYNC_INTERVAL_SECONDS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    *,
    id: str = "evt-1",
    title: str = "Test Event",
    source: str = "local",
    hours_from_now: int = 1,
) -> CalendarEvent:
    now = datetime.now(timezone.utc)
    return CalendarEvent(
        id=id,
        title=title,
        start_time=now + timedelta(hours=hours_from_now),
        end_time=now + timedelta(hours=hours_from_now + 1),
        source=source,
    )


class _FakeGoogleService:
    """Mock Google Calendar service with synchronous methods."""

    def __init__(
        self,
        events: list[CalendarEvent] | None = None,
        raise_on_list: Exception | None = None,
        raise_on_create: Exception | None = None,
    ) -> None:
        self.events = events or []
        self.created: list[CalendarEvent] = []
        self._raise_on_list = raise_on_list
        self._raise_on_create = raise_on_create

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        if self._raise_on_list:
            raise self._raise_on_list
        return list(self.events)

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        if self._raise_on_create:
            raise self._raise_on_create
        self.created.append(event)
        return event.model_copy(update={"source": "google"})


class _FakeCalDAVService:
    """Mock CalDAV service with async methods."""

    def __init__(
        self,
        events: list[CalendarEvent] | None = None,
        raise_on_list: Exception | None = None,
        raise_on_create: Exception | None = None,
    ) -> None:
        self.events = events or []
        self.created: list[CalendarEvent] = []
        self._raise_on_list = raise_on_list
        self._raise_on_create = raise_on_create

    async def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        if self._raise_on_list:
            raise self._raise_on_list
        return list(self.events)

    async def create_event(self, event: CalendarEvent) -> CalendarEvent:
        if self._raise_on_create:
            raise self._raise_on_create
        self.created.append(event)
        return event.model_copy(update={"source": "caldav"})


def _fake_db_factory(events: list | None = None):
    """Return a callable that produces a mock DB session."""
    from unittest.mock import MagicMock

    db_events = events or []

    def factory():
        session = MagicMock()
        query = MagicMock()
        query.filter.return_value.all.return_value = db_events
        session.query.return_value = query
        return session

    return factory


def _make_db_event(
    *,
    id: str = "local-1",
    title: str = "Local Event",
    hours_from_now: int = 2,
) -> SimpleNamespace:
    """Create a fake ORM Event object."""
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        id=id,
        title=title,
        start_time=now + timedelta(hours=hours_from_now),
        end_time=now + timedelta(hours=hours_from_now + 1),
        location=None,
        description=None,
        attendees=[],
        source="local",
        external_id=None,
    )


# ---------------------------------------------------------------------------
# Tests: sync_now() pulls from all sources
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_now_calls_all_sources() -> None:
    """sync_now() should pull from local, Google, and CalDAV."""
    google_events = [_make_event(id="g-1", title="Google Meeting", source="google")]
    caldav_events = [_make_event(id="c-1", title="CalDAV Standup", source="caldav")]
    db_events = [_make_db_event(id="l-1", title="Local Lunch")]

    service = CalendarSyncService(
        google_service=_FakeGoogleService(events=google_events),
        caldav_service=_FakeCalDAVService(events=caldav_events),
        db_factory=_fake_db_factory(db_events),
    )

    results = await service.sync_now()

    assert results["local"] == "ok"
    assert results["google"] == "ok"
    assert results["caldav"] == "ok"

    # Unified events should contain all three
    unified = service.get_unified_events()
    sources = {e.source for e in unified}
    assert "local" in sources
    assert "google" in sources
    assert "caldav" in sources


@pytest.mark.asyncio
async def test_sync_now_without_google_configured() -> None:
    """When Google service is None, sync reports not_configured."""
    service = CalendarSyncService(
        google_service=None,
        caldav_service=None,
        db_factory=_fake_db_factory([]),
    )

    results = await service.sync_now()

    assert results["google"] == "not_configured"
    assert results["caldav"] == "not_configured"
    assert results["local"] == "ok"


@pytest.mark.asyncio
async def test_sync_now_without_db_factory() -> None:
    """When db_factory is None, local pull is skipped."""
    service = CalendarSyncService(
        google_service=None,
        caldav_service=None,
        db_factory=None,
    )

    results = await service.sync_now()

    assert results["local"] == "skipped"


# ---------------------------------------------------------------------------
# Tests: push_event() propagates to configured sources
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_push_event_to_google_and_caldav() -> None:
    """push_event() should create the event in both Google and CalDAV."""
    google = _FakeGoogleService()
    caldav = _FakeCalDAVService()

    service = CalendarSyncService(
        google_service=google,
        caldav_service=caldav,
    )

    event = _make_event(id="push-1", title="New Meeting", source="local")
    result = await service.push_event(event)

    assert len(google.created) == 1
    assert google.created[0].title == "New Meeting"
    assert len(caldav.created) == 1
    assert caldav.created[0].title == "New Meeting"


@pytest.mark.asyncio
async def test_push_event_skips_unconfigured_sources() -> None:
    """push_event() should not fail when sources are None."""
    service = CalendarSyncService(
        google_service=None,
        caldav_service=None,
    )

    event = _make_event(id="push-2", title="Solo Event", source="local")
    result = await service.push_event(event)

    # Should return the event unchanged
    assert result.title == "Solo Event"


@pytest.mark.asyncio
async def test_push_event_handles_google_failure_gracefully() -> None:
    """push_event() should continue to CalDAV even if Google fails."""
    google = _FakeGoogleService(raise_on_create=RuntimeError("Google down"))
    caldav = _FakeCalDAVService()

    service = CalendarSyncService(
        google_service=google,
        caldav_service=caldav,
    )

    event = _make_event(id="push-3", title="Resilient Event", source="local")
    result = await service.push_event(event)

    # Google failed but CalDAV should succeed
    assert len(caldav.created) == 1
    status = service.get_sync_status()
    assert status["google"]["last_error"] is not None


@pytest.mark.asyncio
async def test_push_event_handles_caldav_failure_gracefully() -> None:
    """push_event() should continue even if CalDAV fails."""
    google = _FakeGoogleService()
    caldav = _FakeCalDAVService(raise_on_create=RuntimeError("CalDAV down"))

    service = CalendarSyncService(
        google_service=google,
        caldav_service=caldav,
    )

    event = _make_event(id="push-4", title="Partial Push", source="local")
    result = await service.push_event(event)

    assert len(google.created) == 1
    status = service.get_sync_status()
    assert status["caldav"]["last_error"] is not None


# ---------------------------------------------------------------------------
# Tests: sync status tracking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_status_tracks_per_source() -> None:
    """get_sync_status() should return per-source state after sync."""
    google_events = [_make_event(id="g-1", source="google")]
    caldav_events = [_make_event(id="c-1", source="caldav")]

    service = CalendarSyncService(
        google_service=_FakeGoogleService(events=google_events),
        caldav_service=_FakeCalDAVService(events=caldav_events),
        db_factory=_fake_db_factory([_make_db_event()]),
    )

    await service.sync_now()
    status = service.get_sync_status()

    assert status["local"]["last_sync_at"] is not None
    assert status["local"]["last_error"] is None
    assert status["local"]["event_count"] >= 0

    assert status["google"]["last_sync_at"] is not None
    assert status["google"]["last_error"] is None
    assert status["google"]["event_count"] == 1

    assert status["caldav"]["last_sync_at"] is not None
    assert status["caldav"]["last_error"] is None
    assert status["caldav"]["event_count"] == 1


@pytest.mark.asyncio
async def test_sync_status_records_errors() -> None:
    """Sync status should capture errors from failed sources."""
    google = _FakeGoogleService(raise_on_list=RuntimeError("Auth expired"))

    service = CalendarSyncService(
        google_service=google,
        caldav_service=None,
        db_factory=_fake_db_factory([]),
    )

    await service.sync_now()
    status = service.get_sync_status()

    assert status["google"]["last_error"] is not None
    assert "Auth expired" in status["google"]["last_error"]
    assert status["google"]["last_sync_at"] is None


# ---------------------------------------------------------------------------
# Tests: unified event list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unified_events_sorted_by_start_time() -> None:
    """get_unified_events() should return events sorted by start_time."""
    early = _make_event(id="early", title="Early", source="google", hours_from_now=1)
    late = _make_event(id="late", title="Late", source="caldav", hours_from_now=5)

    service = CalendarSyncService(
        google_service=_FakeGoogleService(events=[early]),
        caldav_service=_FakeCalDAVService(events=[late]),
        db_factory=_fake_db_factory([]),
    )

    await service.sync_now()
    events = service.get_unified_events()

    assert len(events) >= 2
    # Find our test events
    titles = [e.title for e in events]
    early_idx = titles.index("Early")
    late_idx = titles.index("Late")
    assert early_idx < late_idx


@pytest.mark.asyncio
async def test_unified_events_filtered_by_date_range() -> None:
    """get_unified_events(start, end) should filter by date range."""
    now = datetime.now(timezone.utc)
    event = _make_event(
        id="in-range", title="In Range", source="google", hours_from_now=2
    )

    service = CalendarSyncService(
        google_service=_FakeGoogleService(events=[event]),
        caldav_service=None,
        db_factory=_fake_db_factory([]),
    )

    await service.sync_now()

    # Filter to a window that includes the event
    start = now + timedelta(hours=1)
    end = now + timedelta(hours=4)
    events = service.get_unified_events(start=start, end=end)
    assert any(e.id == "in-range" for e in events)

    # Filter to a window that excludes the event
    far_start = now + timedelta(hours=10)
    far_end = now + timedelta(hours=20)
    events = service.get_unified_events(start=far_start, end=far_end)
    assert not any(e.id == "in-range" for e in events)


# ---------------------------------------------------------------------------
# Tests: merge (last-write-wins)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_merge_replaces_events_from_same_source() -> None:
    """Re-syncing a source should replace its events, not duplicate them."""
    google = _FakeGoogleService(
        events=[_make_event(id="g-1", title="V1", source="google")]
    )

    service = CalendarSyncService(
        google_service=google,
        caldav_service=None,
        db_factory=_fake_db_factory([]),
    )

    await service.sync_now()
    assert len([e for e in service.get_unified_events() if e.source == "google"]) == 1

    # Update Google events and re-sync
    google.events = [
        _make_event(id="g-1", title="V2", source="google"),
        _make_event(id="g-2", title="New", source="google"),
    ]
    await service.sync_now()

    google_events = [e for e in service.get_unified_events() if e.source == "google"]
    assert len(google_events) == 2
    titles = {e.title for e in google_events}
    assert "V2" in titles
    assert "New" in titles
    assert "V1" not in titles


# ---------------------------------------------------------------------------
# Tests: background loop with mocked asyncio.sleep
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_background_loop_calls_sync_periodically() -> None:
    """The background loop should call sync_now at the configured interval."""
    service = CalendarSyncService(
        google_service=None,
        caldav_service=None,
        db_factory=_fake_db_factory([]),
    )

    call_count = 0
    original_sync_now = service.sync_now

    async def counting_sync_now():
        nonlocal call_count
        call_count += 1
        return await original_sync_now()

    service.sync_now = counting_sync_now  # type: ignore[assignment]

    with patch(
        "app.services.calendar_sync.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        # Make sleep raise CancelledError after 2 calls to break the loop
        call_idx = 0

        async def limited_sleep(seconds):
            nonlocal call_idx
            call_idx += 1
            if call_idx >= 2:
                raise asyncio.CancelledError()
            # Verify the interval is correct
            assert seconds == SYNC_INTERVAL_SECONDS

        mock_sleep.side_effect = limited_sleep

        await service.start()

        # Wait for the task to complete (it will be cancelled after 2 iterations)
        try:
            await service._task
        except asyncio.CancelledError:
            pass

    assert call_count >= 2


@pytest.mark.asyncio
async def test_start_and_stop_lifecycle() -> None:
    """start() and stop() should manage the background task cleanly."""
    service = CalendarSyncService(
        google_service=None,
        caldav_service=None,
        db_factory=_fake_db_factory([]),
    )

    with patch(
        "app.services.calendar_sync.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        mock_sleep.side_effect = asyncio.CancelledError()

        await service.start()
        assert service._running is True
        assert service._task is not None

        await service.stop()
        assert service._running is False
        assert service._task is None


@pytest.mark.asyncio
async def test_start_is_idempotent() -> None:
    """Calling start() twice should not create duplicate tasks."""
    service = CalendarSyncService(
        google_service=None,
        caldav_service=None,
        db_factory=_fake_db_factory([]),
    )

    with patch(
        "app.services.calendar_sync.asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:
        mock_sleep.side_effect = asyncio.CancelledError()

        await service.start()
        first_task = service._task

        await service.start()
        second_task = service._task

        assert first_task is second_task

        await service.stop()


# ---------------------------------------------------------------------------
# Tests: graceful behavior when sources are unavailable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_google_list_failure_does_not_crash_sync() -> None:
    """If Google list_events raises, sync should continue with other sources."""
    google = _FakeGoogleService(raise_on_list=ConnectionError("Network error"))
    caldav = _FakeCalDAVService(events=[_make_event(id="c-1", source="caldav")])

    service = CalendarSyncService(
        google_service=google,
        caldav_service=caldav,
        db_factory=_fake_db_factory([]),
    )

    results = await service.sync_now()

    assert results["google"] == "error"
    assert results["caldav"] == "ok"

    # CalDAV events should still be in the unified list
    events = service.get_unified_events()
    assert any(e.source == "caldav" for e in events)


@pytest.mark.asyncio
async def test_caldav_list_failure_does_not_crash_sync() -> None:
    """If CalDAV list_events raises, sync should continue with other sources."""
    google = _FakeGoogleService(events=[_make_event(id="g-1", source="google")])
    caldav = _FakeCalDAVService(raise_on_list=ConnectionError("Server down"))

    service = CalendarSyncService(
        google_service=google,
        caldav_service=caldav,
        db_factory=_fake_db_factory([]),
    )

    results = await service.sync_now()

    assert results["google"] == "ok"
    assert results["caldav"] == "error"

    events = service.get_unified_events()
    assert any(e.source == "google" for e in events)


@pytest.mark.asyncio
async def test_all_sources_fail_gracefully() -> None:
    """If all sources fail, sync should not crash and status should reflect errors."""
    google = _FakeGoogleService(raise_on_list=RuntimeError("Google down"))
    caldav = _FakeCalDAVService(raise_on_list=RuntimeError("CalDAV down"))

    def bad_db_factory():
        raise RuntimeError("DB connection failed")

    service = CalendarSyncService(
        google_service=google,
        caldav_service=caldav,
        db_factory=bad_db_factory,
    )

    results = await service.sync_now()

    assert results["local"] == "error"
    assert results["google"] == "error"
    assert results["caldav"] == "error"

    status = service.get_sync_status()
    assert status["local"]["last_error"] is not None
    assert status["google"]["last_error"] is not None
    assert status["caldav"]["last_error"] is not None
