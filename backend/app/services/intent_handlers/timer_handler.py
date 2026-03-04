"""Voice-driven timer and alarm intent handler.

Routes timer intents (set, query, cancel) to the TimerService
and returns TTS-friendly response strings.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.schemas.intent import Intent
from app.services.timers import TimerService

LOGGER = logging.getLogger(__name__)

# Intent names from sentences.ini / NLU
_SET_TIMER = "set_timer"
_CANCEL_TIMER = "cancel_timer"
_QUERY_TIMER = "query_timer"

# Word-to-number mapping for common spoken durations
_WORD_NUMBERS: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "ninety": 90,
    "a": 1,
    "an": 1,
    "half": 30,
}

# Multipliers for time units
_UNIT_SECONDS: dict[str, int] = {
    "second": 1,
    "seconds": 1,
    "sec": 1,
    "secs": 1,
    "minute": 60,
    "minutes": 60,
    "min": 60,
    "mins": 60,
    "hour": 3600,
    "hours": 3600,
    "hr": 3600,
    "hrs": 3600,
}


def _get_slot(intent: Intent, name: str) -> Optional[str]:
    """Extract a named slot value from an intent."""
    for slot in intent.slots:
        if slot.name == name:
            return slot.value.strip() if slot.value else None
    return None


def _parse_duration_seconds(text: str) -> Optional[int]:
    """Parse a natural-language duration string into seconds.

    Handles patterns like:
    - "five minutes"
    - "10 minutes"
    - "1 hour and 30 minutes"
    - "a minute and a half"
    - "90 seconds"
    """
    if not text:
        return None

    text = text.lower().strip()

    # Try to find all (number, unit) pairs
    total = 0
    found = False

    # Pattern: number/word followed by a time unit
    word_alts = "|".join(
        re.escape(w) for w in sorted(_WORD_NUMBERS, key=len, reverse=True)
    )
    unit_alts = "|".join(
        re.escape(u) for u in sorted(_UNIT_SECONDS, key=len, reverse=True)
    )
    pattern = re.compile(
        r"(\d+|" + word_alts + r")"
        r"\s*(?:and\s+a\s+half\s+)?"
        r"(" + unit_alts + r")"
    )

    for match in pattern.finditer(text):
        num_str = match.group(1)
        unit_str = match.group(2)

        if num_str.isdigit():
            number = int(num_str)
        else:
            number = _WORD_NUMBERS.get(num_str, 0)

        multiplier = _UNIT_SECONDS.get(unit_str, 0)
        total += number * multiplier
        found = True

    # Handle "half" as a standalone modifier (e.g. "a minute and a half")
    if "and a half" in text and found:
        # Find the last unit mentioned and add half of it
        for unit, secs in [("hour", 3600), ("minute", 60), ("second", 1)]:
            if unit in text:
                total += secs // 2
                break

    if found and total > 0:
        return total

    # Fallback: try bare number (assume minutes)
    bare_match = re.match(r"^(\d+)$", text.strip())
    if bare_match:
        return int(bare_match.group(1)) * 60

    return None


def _format_duration(seconds: int) -> str:
    """Format seconds into a spoken duration string."""
    if seconds <= 0:
        return "0 seconds"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs and not hours:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")

    return " and ".join(parts)


class TimerIntentHandler:
    """Handle timer and alarm voice intents."""

    def __init__(self, timer_service: TimerService) -> None:
        self._timers = timer_service

    async def handle(self, intent: Intent) -> str:
        """Route to set/query/cancel based on intent name."""
        if intent.name == _SET_TIMER:
            return self._handle_set_timer(intent)
        if intent.name == _QUERY_TIMER:
            return self._handle_query_timer(intent)
        if intent.name == _CANCEL_TIMER:
            return self._handle_cancel_timer(intent)

        return "I'm not sure how to handle that timer request."

    def _handle_set_timer(self, intent: Intent) -> str:
        """Parse slots and create a timer."""
        duration_text = _get_slot(intent, "duration")
        name = _get_slot(intent, "name") or "timer"

        if not duration_text:
            return "How long should I set the timer for?"

        seconds = _parse_duration_seconds(duration_text)
        if seconds is None or seconds <= 0:
            return f"I couldn't understand the duration '{duration_text}'."

        timer = self._timers.set_timer(name=name, duration_seconds=seconds)
        spoken = _format_duration(timer.duration_seconds or seconds)
        return f"{name.capitalize()} timer set for {spoken}."

    def _handle_query_timer(self, intent: Intent) -> str:
        """Report remaining time on active timers."""
        name = _get_slot(intent, "name")
        timers = self._timers.get_timers()

        if not timers:
            return "You don't have any active timers."

        if name:
            search = name.lower()
            timers = [t for t in timers if search in t.name.lower()]
            if not timers:
                return f"I couldn't find a timer called {name}."

        lines: list[str] = []
        for timer in timers:
            remaining = TimerService.remaining_seconds(timer)
            spoken = _format_duration(remaining)
            lines.append(f"Your {timer.name} timer has {spoken} remaining.")

        return " ".join(lines)

    def _handle_cancel_timer(self, intent: Intent) -> str:
        """Cancel a timer by name or cancel all."""
        name = _get_slot(intent, "name")

        if name and name.lower() == "all":
            count = self._timers.cancel_all_timers()
            if count == 0:
                return "You don't have any active timers to cancel."
            noun = "timer" if count == 1 else "timers"
            return f"Cancelled {count} {noun}."

        if name:
            count = self._timers.cancel_timer_by_name(name)
            if count == 0:
                return f"I couldn't find an active timer called {name}."
            return f"Cancelled your {name} timer."

        # No name specified — cancel the most recent active timer
        timers = self._timers.get_timers()
        if not timers:
            return "You don't have any active timers to cancel."

        self._timers.cancel_timer(timers[0].id)
        return f"Cancelled your {timers[0].name} timer."
