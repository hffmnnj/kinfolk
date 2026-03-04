"""Tests for CalDAV calendar source integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.services.calendar_caldav import CalDAVCalendarService, CalendarEvent


class _FakeDeleteItem:
    def __init__(self) -> None:
        self.deleted = False

    def delete(self) -> None:
        self.deleted = True


class _FakeCalendar:
    def __init__(self, name: str, events: list[object] | None = None) -> None:
        self.name = name
        self._events = events or []
        self.saved_payloads: list[str] = []
        self.search_results: dict[str, list[_FakeDeleteItem]] = {}

    def date_search(self, start: datetime, end: datetime) -> list[object]:
        del start, end
        return list(self._events)

    def save_event(self, payload: str) -> object:
        self.saved_payloads.append(payload)
        return self._events[0]

    def search(self, *, event_id: str) -> list[_FakeDeleteItem]:
        return list(self.search_results.get(event_id, []))


class _FakePrincipal:
    def __init__(self, calendars: list[_FakeCalendar]) -> None:
        self._calendars = calendars

    def calendars(self) -> list[_FakeCalendar]:
        return list(self._calendars)


class _FakeClient:
    def __init__(self, calendars: list[_FakeCalendar]) -> None:
        self._principal = _FakePrincipal(calendars)

    def principal(self) -> _FakePrincipal:
        return self._principal


def _raw_event(
    *,
    uid: str,
    title: str,
    start: datetime,
    end: datetime,
    description: str = "",
    location: str = "",
) -> object:
    vevent = SimpleNamespace(
        uid=SimpleNamespace(value=uid),
        summary=SimpleNamespace(value=title),
        dtstart=SimpleNamespace(value=start),
        dtend=SimpleNamespace(value=end),
        description=SimpleNamespace(value=description),
        location=SimpleNamespace(value=location),
    )
    return SimpleNamespace(vobject_instance=SimpleNamespace(vevent=vevent), id=uid)


def _settings(servers: list[dict]) -> SimpleNamespace:
    return SimpleNamespace(caldav_servers=servers)


@pytest.mark.asyncio
async def test_list_events_with_mocked_caldav_client() -> None:
    start = datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    event = _raw_event(uid="evt-1", title="Dentist", start=start, end=end)
    calendar = _FakeCalendar(name="personal", events=[event])

    service = CalDAVCalendarService(
        app_settings=_settings(
            [
                {
                    "url": "https://dav.example.com/",
                    "username": "user",
                    "password": "pass",
                    "calendar_name": "personal",
                }
            ]
        ),
        client_factory=lambda **kwargs: _FakeClient([calendar]),
    )

    events = await service.list_events(start=start, end=end)

    assert len(events) == 1
    assert getattr(events[0], "id", getattr(events[0], "event_id", "")) == "evt-1"
    assert getattr(events[0], "title") == "Dentist"


@pytest.mark.asyncio
async def test_create_event_with_mocked_caldav_client() -> None:
    start = datetime(2026, 3, 7, 9, 30, tzinfo=timezone.utc)
    end = start + timedelta(hours=2)
    created = _raw_event(uid="evt-created", title="Lunch", start=start, end=end)
    calendar = _FakeCalendar(name="personal", events=[created])

    service = CalDAVCalendarService(
        app_settings=_settings(
            [
                {
                    "url": "https://dav.example.com/",
                    "username": "user",
                    "password": "pass",
                    "calendar_name": "personal",
                }
            ]
        ),
        client_factory=lambda **kwargs: _FakeClient([calendar]),
    )

    input_event = CalendarEvent(
        id="local-1",
        title="Lunch",
        start_time=start,
        end_time=end,
        description="Team lunch",
        location="Cafe",
    )

    result = await service.create_event(input_event)

    assert calendar.saved_payloads
    assert "BEGIN:VEVENT" in calendar.saved_payloads[0]
    assert "SUMMARY:Lunch" in calendar.saved_payloads[0]
    assert getattr(result, "id", getattr(result, "event_id", "")) == "evt-created"


@pytest.mark.asyncio
async def test_delete_event_with_mocked_caldav_client() -> None:
    item = _FakeDeleteItem()
    calendar = _FakeCalendar(name="personal", events=[])
    calendar.search_results["evt-delete"] = [item]

    service = CalDAVCalendarService(
        app_settings=_settings(
            [
                {
                    "url": "https://dav.example.com/",
                    "username": "user",
                    "password": "pass",
                }
            ]
        ),
        client_factory=lambda **kwargs: _FakeClient([calendar]),
    )

    await service.delete_event("evt-delete")

    assert item.deleted is True


@pytest.mark.asyncio
async def test_multiple_server_aggregation() -> None:
    start = datetime(2026, 3, 8, 8, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)

    event_a = _raw_event(uid="a-1", title="A", start=start, end=end)
    event_b = _raw_event(uid="b-1", title="B", start=start, end=end)

    calendar_a = _FakeCalendar(name="cal-a", events=[event_a])
    calendar_b = _FakeCalendar(name="cal-b", events=[event_b])

    clients = {
        "https://dav-a.example.com/": _FakeClient([calendar_a]),
        "https://dav-b.example.com/": _FakeClient([calendar_b]),
    }

    service = CalDAVCalendarService(
        app_settings=_settings(
            [
                {
                    "url": "https://dav-a.example.com/",
                    "username": "user-a",
                    "password": "pass-a",
                },
                {
                    "url": "https://dav-b.example.com/",
                    "username": "user-b",
                    "password": "pass-b",
                },
            ]
        ),
        client_factory=lambda **kwargs: clients[kwargs["url"]],
    )

    events = await service.list_events(start=start, end=end)

    ids = {getattr(e, "id", getattr(e, "event_id", "")) for e in events}
    assert ids == {"a-1", "b-1"}


@pytest.mark.asyncio
async def test_no_servers_configured_graceful_handling() -> None:
    service = CalDAVCalendarService(app_settings=_settings([]), client_factory=None)

    start = datetime(2026, 3, 9, 8, 0, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    events = await service.list_events(start=start, end=end)

    assert events == []
    await service.delete_event("missing")
