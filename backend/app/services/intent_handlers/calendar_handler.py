"""Voice-driven calendar CRUD intent handler.

Routes calendar intents (add, query, delete) to the calendar sync
service and returns TTS-friendly response strings.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from dateutil import parser as dateutil_parser

from app.domain.calendar_event import CalendarEvent
from app.schemas.intent import Intent
from app.services.calendar_sync import CalendarSyncService

LOGGER = logging.getLogger(__name__)

# Intent names from sentences.ini / NLU
_ADD_EVENT = "add_calendar_event"
_GET_EVENTS = "get_calendar"
_DELETE_EVENT = "cancel_calendar_event"

# Default event duration when only a start time is provided
_DEFAULT_DURATION = timedelta(hours=1)


def _get_slot(intent: Intent, name: str) -> Optional[str]:
    """Extract a named slot value from an intent."""
    for slot in intent.slots:
        if slot.name == name:
            return slot.value.strip() if slot.value else None
    return None


def _resolve_relative_date(
    text: str,
    reference: datetime,
) -> tuple[str, datetime]:
    """Pre-process relative day words dateutil handles poorly.

    Returns ``(cleaned_text, base_date)`` where *base_date* is the
    midnight of the day the text refers to.
    """
    lowered = text.lower().strip()
    base = reference.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    if lowered.startswith("tomorrow"):
        remainder = lowered.replace("tomorrow", "", 1).strip()
        return (remainder or "12:00", base + timedelta(days=1))

    if lowered.startswith("today"):
        remainder = lowered.replace("today", "", 1).strip()
        return (remainder or "12:00", base)

    return (text, base)


def _parse_datetime_nearest_future(
    text: str,
    reference: Optional[datetime] = None,
) -> Optional[datetime]:
    """Parse a natural-language date/time string.

    Uses python-dateutil for parsing.  When the result is ambiguous
    (e.g. "Friday" without specifying which week), the nearest
    *future* occurrence is returned per the BLUEPRINT decision.
    """
    if reference is None:
        reference = datetime.now(timezone.utc)

    if not text:
        return None

    cleaned, base_date = _resolve_relative_date(text, reference)

    try:
        parsed = dateutil_parser.parse(
            cleaned,
            default=base_date,
            fuzzy=True,
        )
    except (ValueError, OverflowError):
        return None

    # Ensure timezone-aware
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    # Nearest-future rule: if the parsed time is in the past,
    # bump forward by one day.
    if parsed <= reference:
        parsed += timedelta(days=1)

    return parsed


def _format_event_time(dt: datetime) -> str:
    """Format a datetime for spoken TTS output."""
    now = datetime.now(timezone.utc)
    delta = dt.date() - now.date()

    if delta.days == 0:
        day_label = "today"
    elif delta.days == 1:
        day_label = "tomorrow"
    elif delta.days == -1:
        day_label = "yesterday"
    else:
        day_label = dt.strftime("%A, %B %d")

    time_label = dt.strftime("%-I:%M %p").lower()
    return f"{day_label} at {time_label}"


def _format_event_list(events: list[CalendarEvent]) -> str:
    """Build a spoken summary of a list of events."""
    if not events:
        return "You have no events scheduled."

    count = len(events)
    noun = "event" if count == 1 else "events"
    lines = [f"You have {count} {noun}."]
    for event in events:
        time_str = _format_event_time(event.start_time)
        lines.append(f"{event.title} at {time_str}.")

    return " ".join(lines)


class CalendarIntentHandler:
    """Handle calendar-related voice intents."""

    def __init__(
        self,
        calendar_sync_service: CalendarSyncService,
    ) -> None:
        self._sync = calendar_sync_service

    async def handle(self, intent: Intent) -> str:
        """Route to create/query/delete based on intent name."""
        if intent.name == _ADD_EVENT:
            return await self._handle_add_event(intent)
        if intent.name == _GET_EVENTS:
            return await self._handle_get_events(intent)
        if intent.name == _DELETE_EVENT:
            return await self._handle_delete_event(intent)

        return "I'm not sure how to handle that calendar request."

    async def _handle_add_event(self, intent: Intent) -> str:
        """Parse slots and create a calendar event."""
        event_title = _get_slot(intent, "event")
        when_text = _get_slot(intent, "when")

        if not event_title:
            return "I need an event name to add to your calendar."

        now = datetime.now(timezone.utc)
        start_time = _parse_datetime_nearest_future(
            when_text or "",
            reference=now,
        )

        if start_time is None:
            # Fall back to one hour from now
            start_time = now + _DEFAULT_DURATION
            time_description = _format_event_time(start_time)
            LOGGER.info(
                "No parseable time in '%s'; defaulting to %s",
                when_text,
                time_description,
            )

        end_time = start_time + _DEFAULT_DURATION

        event = CalendarEvent(
            title=event_title,
            start_time=start_time,
            end_time=end_time,
            source="local",
        )

        try:
            await self._sync.push_event(event)
        except Exception:
            LOGGER.exception("Failed to push calendar event")
            return f"Sorry, I couldn't add {event_title} to your calendar."

        time_str = _format_event_time(start_time)
        return f"I've added {event_title} for {time_str}."

    async def _handle_get_events(self, intent: Intent) -> str:
        """Query events for today or a specified date."""
        when_text = _get_slot(intent, "when")

        now = datetime.now(timezone.utc)

        if when_text:
            target = _parse_datetime_nearest_future(
                when_text,
                reference=now,
            )
            if target is None:
                target = now
        else:
            target = now

        day_start = target.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        day_end = day_start + timedelta(days=1)

        events = self._sync.get_unified_events(
            start=day_start,
            end=day_end,
        )

        return _format_event_list(events)

    async def _handle_delete_event(self, intent: Intent) -> str:
        """Find and remove an event by title match."""
        event_text = _get_slot(intent, "event")

        if not event_text:
            return "Which event would you like to cancel?"

        search_term = event_text.lower()

        # Search all cached events so the user can cancel events
        # happening right now or very recently added.
        all_events = self._sync.get_unified_events()

        match: Optional[CalendarEvent] = None
        for event in all_events:
            if search_term in event.title.lower():
                match = event
                break

        if match is None:
            return (
                "I couldn't find an event matching "
                f"'{event_text}' on your calendar."
            )

        # Remove from cached events
        self._sync._cached_events = [
            e for e in self._sync._cached_events if e is not match
        ]

        return f"I've cancelled {match.title}."
