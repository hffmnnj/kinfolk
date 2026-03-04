"""Background calendar sync scheduler.

Pulls from all sources, pushes local changes.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.domain.calendar_event import CalendarEvent

LOGGER = logging.getLogger(__name__)

SYNC_INTERVAL_SECONDS = 300  # 5 minutes
PULL_WINDOW_DAYS = 30  # How far ahead to pull events


class SourceSyncStatus:
    """Per-source sync tracking."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.last_sync_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.event_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "last_sync_at": (
                self.last_sync_at.isoformat() if self.last_sync_at else None
            ),
            "last_error": self.last_error,
            "event_count": self.event_count,
        }


class CalendarSyncService:
    """Unified calendar sync across Google, CalDAV, local.

    Pulls events from all configured sources every 5 minutes.
    Pushes local event changes to configured sources immediately.
    """

    def __init__(
        self,
        google_service: Any | None = None,
        caldav_service: Any | None = None,
        db_factory: Any | None = None,
        settings: Any | None = None,
    ) -> None:
        self._google = google_service
        self._caldav = caldav_service
        self._db_factory = db_factory
        self._settings = settings
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False

        self._source_status: dict[str, SourceSyncStatus] = {
            "local": SourceSyncStatus("local"),
            "google": SourceSyncStatus("google"),
            "caldav": SourceSyncStatus("caldav"),
        }

        self._cached_events: list[CalendarEvent] = []

    async def start(self) -> None:
        """Start the background 5-minute pull loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        LOGGER.info(
            "Calendar sync started (interval=%ds)",
            SYNC_INTERVAL_SECONDS,
        )

    async def stop(self) -> None:
        """Graceful shutdown of the sync loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        LOGGER.info("Calendar sync scheduler stopped")

    async def sync_now(self) -> dict[str, str]:
        """Manual trigger — pull all sources.

        Returns ``{source: status}`` dict.
        """
        results: dict[str, str] = {}

        results["local"] = await self._pull_local()
        results["google"] = await self._pull_google()
        results["caldav"] = await self._pull_caldav()

        return results

    async def push_event(
        self,
        event: CalendarEvent,
    ) -> CalendarEvent:
        """Push a local event to all configured sources.

        Returns the event (potentially updated with external IDs).
        """
        pushed = event

        if self._google is not None:
            try:
                result = self._google.create_event(event)
                if isinstance(result, CalendarEvent):
                    pushed = result
                status = self._source_status["google"]
                status.last_error = None
                LOGGER.info(
                    "Pushed event '%s' to Google Calendar",
                    event.title,
                )
            except Exception as exc:
                LOGGER.warning(
                    "Failed to push to Google Calendar: %s",
                    exc,
                )
                self._source_status["google"].last_error = str(exc)

        if self._caldav is not None:
            try:
                result = await self._caldav.create_event(event)
                if isinstance(result, CalendarEvent):
                    pushed = result
                status = self._source_status["caldav"]
                status.last_error = None
                LOGGER.info(
                    "Pushed event '%s' to CalDAV",
                    event.title,
                )
            except Exception as exc:
                LOGGER.warning(
                    "Failed to push to CalDAV: %s",
                    exc,
                )
                self._source_status["caldav"].last_error = str(exc)

        return pushed

    def get_unified_events(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[CalendarEvent]:
        """Return cached unified event list filtered by range."""
        events = list(self._cached_events)

        if start is not None:
            events = [e for e in events if e.end_time >= start]
        if end is not None:
            events = [e for e in events if e.start_time <= end]

        events.sort(key=lambda e: e.start_time)
        return events

    def get_sync_status(self) -> dict[str, Any]:
        """Return per-source sync status."""
        return {n: s.to_dict() for n, s in self._source_status.items()}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _sync_loop(self) -> None:
        """Background loop: pull every SYNC_INTERVAL_SECONDS."""
        while self._running:
            try:
                await self.sync_now()
            except Exception as exc:
                LOGGER.error("Sync loop error: %s", exc)

            try:
                await asyncio.sleep(SYNC_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break

    async def _pull_local(self) -> str:
        """Pull events from local SQLite database."""
        status = self._source_status["local"]
        try:
            if self._db_factory is None:
                status.last_error = "No database factory configured"
                return "skipped"

            db: Session = self._db_factory()
            try:
                from app.models.event import Event

                now = datetime.now(timezone.utc)
                window_end = now + timedelta(
                    days=PULL_WINDOW_DAYS,
                )

                db_events = (
                    db.query(Event)
                    .filter(
                        Event.end_time >= now,
                        Event.start_time <= window_end,
                    )
                    .all()
                )

                local_events = self._map_db_events(
                    db_events,
                )
                self._merge_events("local", local_events)
                status.last_sync_at = datetime.now(
                    timezone.utc,
                )
                status.last_error = None
                status.event_count = len(local_events)
                return "ok"
            finally:
                db.close()

        except Exception as exc:
            LOGGER.warning(
                "Failed to pull local events: %s",
                exc,
            )
            status.last_error = str(exc)
            return "error"

    async def _pull_google(self) -> str:
        """Pull events from Google Calendar."""
        status = self._source_status["google"]

        if self._google is None:
            status.last_error = None
            return "not_configured"

        try:
            now = datetime.now(timezone.utc)
            window_end = now + timedelta(
                days=PULL_WINDOW_DAYS,
            )
            events = self._google.list_events(
                start=now,
                end=window_end,
            )

            self._merge_events("google", events)
            status.last_sync_at = datetime.now(timezone.utc)
            status.last_error = None
            status.event_count = len(events)
            return "ok"

        except Exception as exc:
            LOGGER.warning(
                "Failed to pull Google Calendar: %s",
                exc,
            )
            status.last_error = str(exc)
            return "error"

    async def _pull_caldav(self) -> str:
        """Pull events from CalDAV sources."""
        status = self._source_status["caldav"]

        if self._caldav is None:
            status.last_error = None
            return "not_configured"

        try:
            now = datetime.now(timezone.utc)
            window_end = now + timedelta(
                days=PULL_WINDOW_DAYS,
            )
            events = await self._caldav.list_events(
                start=now,
                end=window_end,
            )

            self._merge_events("caldav", events)
            status.last_sync_at = datetime.now(timezone.utc)
            status.last_error = None
            status.event_count = len(events)
            return "ok"

        except Exception as exc:
            LOGGER.warning(
                "Failed to pull CalDAV events: %s",
                exc,
            )
            status.last_error = str(exc)
            return "error"

    def _merge_events(
        self,
        source: str,
        new_events: list[CalendarEvent],
    ) -> None:
        """Merge events (last-write-wins)."""
        kept = [e for e in self._cached_events if e.source != source]
        self._cached_events = kept
        self._cached_events.extend(new_events)

    @staticmethod
    def _map_db_events(db_events: list) -> list[CalendarEvent]:
        """Convert ORM Event rows to CalendarEvent domain objects."""
        result: list[CalendarEvent] = []
        for db_event in db_events:
            result.append(
                CalendarEvent(
                    id=db_event.id,
                    title=db_event.title,
                    start_time=db_event.start_time,
                    end_time=db_event.end_time,
                    location=db_event.location,
                    description=db_event.description,
                    attendees=db_event.attendees or [],
                    source="local",
                    external_id=getattr(
                        db_event,
                        "external_id",
                        None,
                    ),
                )
            )
        return result
