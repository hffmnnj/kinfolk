"""CalDAV calendar source integration service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from importlib import import_module
from typing import Any
from uuid import uuid4

from app.config import settings

try:
    domain_calendar_event = import_module("app.domain.calendar_event")
    CalendarEvent = getattr(domain_calendar_event, "CalendarEvent")
except ModuleNotFoundError:

    @dataclass(slots=True)
    class CalendarEvent:
        """Fallback CalendarEvent shape for parallel task execution."""

        id: str
        title: str
        start_time: datetime
        end_time: datetime
        description: str | None = None
        location: str | None = None
        source: str = "caldav"


class CalDAVCalendarService:
    """Calendar source adapter for one or more CalDAV servers."""

    def __init__(
        self,
        app_settings: Any = settings,
        client_factory: Any | None = None,
    ):
        self._settings = app_settings
        self._client_factory = client_factory or self._default_client_factory

    async def list_events(
        self,
        start: datetime,
        end: datetime,
    ) -> list[CalendarEvent]:
        """List events from all configured CalDAV servers."""
        if not self._server_configs:
            return []

        events: list[CalendarEvent] = []

        for config in self._server_configs:
            try:
                for calendar in self._calendars_for_config(config):
                    for raw_event in calendar.date_search(start, end):
                        parsed = self._to_calendar_event(raw_event, config)
                        if parsed is not None:
                            events.append(parsed)
            except Exception:
                continue

        return events

    async def create_event(self, event: CalendarEvent) -> CalendarEvent:
        """Create an event in the first available CalDAV calendar."""
        if not self._server_configs:
            return event

        config = self._server_configs[0]
        calendars = self._calendars_for_config(config)
        if not calendars:
            return event

        calendar = calendars[0]
        ical_data = self._build_icalendar(event)
        created = calendar.save_event(ical_data)
        created_event = self._to_calendar_event(created, config)
        return created_event or event

    async def delete_event(self, event_id: str) -> None:
        """Delete an event from configured CalDAV calendars by event id."""
        if not self._server_configs:
            return

        for config in self._server_configs:
            try:
                for calendar in self._calendars_for_config(config):
                    matches = calendar.search(event_id=event_id)
                    for item in matches:
                        item.delete()
                    if matches:
                        return
            except Exception:
                continue

    @property
    def _server_configs(self) -> list[dict[str, Any]]:
        configs: list[dict[str, Any]] = []
        raw_configs = getattr(self._settings, "caldav_servers", []) or []

        for entry in raw_configs:
            url = str(entry.get("url", "")).strip()
            username = str(entry.get("username", "")).strip()
            password = str(entry.get("password", "")).strip()
            if not (url and username and password):
                continue

            calendar_name = entry.get("calendar_name")
            configs.append(
                {
                    "url": url,
                    "username": username,
                    "password": password,
                    "calendar_name": str(calendar_name).strip()
                    if calendar_name
                    else None,
                }
            )

        return configs

    def _default_client_factory(
        self,
        *,
        url: str,
        username: str,
        password: str,
    ) -> Any:
        try:
            caldav = import_module("caldav")
        except ImportError as exc:
            raise RuntimeError("caldav dependency is not installed") from exc

        return caldav.DAVClient(url=url, username=username, password=password)

    def _calendars_for_config(self, config: dict[str, Any]) -> list[Any]:
        client = self._client_factory(
            url=config["url"],
            username=config["username"],
            password=config["password"],
        )
        principal = client.principal()
        calendars = list(principal.calendars())

        name = config.get("calendar_name")
        if not name:
            return calendars

        return [
            calendar
            for calendar in calendars
            if getattr(calendar, "name", None) == name
        ]

    def _to_calendar_event(
        self,
        raw_event: Any,
        config: dict[str, Any],
    ) -> CalendarEvent | None:
        vobject_instance = getattr(raw_event, "vobject_instance", None)
        vevent = getattr(vobject_instance, "vevent", None)
        if vevent is None:
            return None

        event_id = self._first_non_empty(
            self._vevent_value(vevent, "uid"),
            getattr(raw_event, "id", ""),
        )
        if not event_id:
            event_id = str(uuid4())

        title = self._first_non_empty(
            self._vevent_value(vevent, "summary"),
            "Untitled",
        )
        start_dt = self._coerce_datetime(self._vevent_value(vevent, "dtstart"))
        end_dt = self._coerce_datetime(self._vevent_value(vevent, "dtend"))

        if start_dt is None:
            return None
        if end_dt is None:
            end_dt = start_dt + timedelta(hours=1)

        description = self._vevent_text(vevent, "description")
        location = self._vevent_text(vevent, "location")

        return self._build_calendar_event(
            event_id=event_id,
            title=title,
            start_time=start_dt,
            end_time=end_dt,
            description=description,
            location=location,
            source=config["url"],
        )

    def _build_icalendar(self, event: CalendarEvent) -> str:
        event_id = self._event_field(event, "id", "event_id") or str(uuid4())
        title = self._event_field(event, "title", "summary") or "Untitled"
        description = self._event_field(event, "description") or ""
        location = self._event_field(event, "location") or ""

        start_dt = self._event_datetime_field(event, "start_time", "start")
        end_dt = self._event_datetime_field(event, "end_time", "end")

        if start_dt is None:
            start_dt = datetime.now(timezone.utc)
        if end_dt is None:
            end_dt = start_dt + timedelta(hours=1)

        return (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//Kinfolk//Calendar//EN\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{event_id}\r\n"
            f"SUMMARY:{title}\r\n"
            f"DTSTART:{self._format_ical_datetime(start_dt)}\r\n"
            f"DTEND:{self._format_ical_datetime(end_dt)}\r\n"
            f"DESCRIPTION:{description}\r\n"
            f"LOCATION:{location}\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )

    def _build_calendar_event(
        self,
        *,
        event_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        description: str | None,
        location: str | None,
        source: str,
    ) -> CalendarEvent:
        constructor_options = [
            {
                "id": event_id,
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "description": description,
                "location": location,
                "source": source,
            },
            {
                "event_id": event_id,
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "description": description,
                "location": location,
                "source": source,
            },
            {
                "id": event_id,
                "title": title,
                "start": start_time,
                "end": end_time,
                "description": description,
                "location": location,
                "source": source,
            },
            {
                "event_id": event_id,
                "title": title,
                "start": start_time,
                "end": end_time,
                "description": description,
                "location": location,
                "source": source,
            },
        ]

        for payload in constructor_options:
            try:
                return CalendarEvent(**payload)
            except TypeError:
                continue

        raise TypeError("Unable to construct CalendarEvent")

    def _event_field(self, event: CalendarEvent, *keys: str) -> str | None:
        for key in keys:
            value = getattr(event, key, None)
            if value is not None:
                text = str(value).strip()
                if text:
                    return text
        return None

    def _event_datetime_field(
        self, event: CalendarEvent, *keys: str
    ) -> datetime | None:
        for key in keys:
            value = getattr(event, key, None)
            parsed = self._coerce_datetime(value)
            if parsed is not None:
                return parsed
        return None

    def _vevent_value(
        self,
        vevent: Any,
        attr: str,
    ) -> str | datetime | date | None:
        field = getattr(vevent, attr, None)
        if field is None:
            return None

        value = getattr(field, "value", field)
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    def _vevent_text(self, vevent: Any, attr: str) -> str | None:
        value = self._vevent_value(vevent, attr)
        if isinstance(value, str):
            return value
        return None

    def _coerce_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)

        if isinstance(value, date):
            return datetime(
                value.year,
                value.month,
                value.day,
                tzinfo=timezone.utc,
            )

        return None

    def _format_ical_datetime(self, value: datetime) -> str:
        normalized = self._coerce_datetime(value)
        if normalized is None:
            normalized = datetime.now(timezone.utc)
        return normalized.strftime("%Y%m%dT%H%M%SZ")

    def _first_non_empty(self, *values: Any) -> str:
        for value in values:
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""
