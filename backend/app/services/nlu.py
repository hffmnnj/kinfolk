"""Rule-based NLU service using sentences.ini-style patterns."""

from __future__ import annotations

import configparser
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.schemas.intent import Intent, IntentCategory, IntentSlot


DEFAULT_SENTENCES: dict[str, list[str]] = {
    "get_calendar": [
        "what's on my calendar",
        "what is on my calendar",
        "show my calendar",
    ],
    "add_calendar_event": [
        "add {event} {when}",
        "add event {event} {when}",
    ],
    "cancel_calendar_event": [
        "cancel {event}",
        "cancel event {event}",
    ],
    "add_task": [
        "add {item} to (my|the) {list_name} list",
        "add {item} to my list",
    ],
    "get_tasks": [
        "what's on my {list_name} list",
        "what is on my {list_name} list",
        "show my {list_name} list",
    ],
    "complete_task": [
        "mark {item} as done",
        "complete {item}",
    ],
    "get_weather": [
        "what's the weather",
        "weather today",
        "forecast",
    ],
    "set_timer": [
        "set a timer for {duration}",
        "set {name} timer",
        "set {name} timer for {duration}",
    ],
    "cancel_timer": [
        "cancel timer",
        "cancel {name} timer",
    ],
    "query_timer": [
        "how long",
        "how long left",
    ],
    "play_music": [
        "play {track}",
        "play music",
    ],
    "pause_music": ["pause music", "pause"],
    "next_song": ["skip", "next song", "next"],
    "set_volume": ["volume up", "volume down", "volume {level}"],
    "turn_device": ["turn on {device}", "turn off {device}"],
    "set_device": ["set {device} to {value}"],
    "activate_scene": ["activate {scene}", "activate {scene} scene"],
    "show_photo_frame": ["show photo frame"],
    "stop_system": ["stop"],
    "sleep_system": ["sleep"],
}


INTENT_CATEGORY_MAP: dict[str, IntentCategory] = {
    "get_calendar": IntentCategory.CALENDAR,
    "add_calendar_event": IntentCategory.CALENDAR,
    "cancel_calendar_event": IntentCategory.CALENDAR,
    "add_task": IntentCategory.TASKS,
    "get_tasks": IntentCategory.TASKS,
    "complete_task": IntentCategory.TASKS,
    "get_weather": IntentCategory.WEATHER,
    "set_timer": IntentCategory.TIMERS,
    "cancel_timer": IntentCategory.TIMERS,
    "query_timer": IntentCategory.TIMERS,
    "play_music": IntentCategory.MUSIC,
    "pause_music": IntentCategory.MUSIC,
    "next_song": IntentCategory.MUSIC,
    "set_volume": IntentCategory.MUSIC,
    "turn_device": IntentCategory.SMARTHOME,
    "set_device": IntentCategory.SMARTHOME,
    "activate_scene": IntentCategory.SMARTHOME,
    "show_photo_frame": IntentCategory.SYSTEM,
    "stop_system": IntentCategory.SYSTEM,
    "sleep_system": IntentCategory.SYSTEM,
}


CATEGORY_KEYWORDS: dict[IntentCategory, tuple[str, ...]] = {
    IntentCategory.CALENDAR: ("calendar", "event"),
    IntentCategory.TASKS: ("task", "list", "done"),
    IntentCategory.WEATHER: ("weather", "forecast", "rain", "temperature"),
    IntentCategory.TIMERS: ("timer", "alarm", "minutes", "seconds", "hours"),
    IntentCategory.MUSIC: ("music", "song", "play", "pause", "volume", "skip"),
    IntentCategory.SMARTHOME: (
        "turn on",
        "turn off",
        "light",
        "scene",
        "device",
        "thermostat",
    ),
    IntentCategory.SYSTEM: ("show", "photo", "stop", "sleep"),
}


@dataclass(frozen=True)
class CompiledPattern:
    intent_name: str
    category: IntentCategory
    regex: re.Pattern[str]
    specificity: int


class NLUService:
    """Parse text into structured intents via regex and keyword matching."""

    def __init__(self, settings) -> None:
        threshold = getattr(settings, "nlu_confidence_threshold", 0.5)
        self._threshold = float(threshold)
        self._sentences_path = Path(
            getattr(
                settings,
                "sentences_ini_path",
                "./backend/rhasspy/sentences.ini",
            )
        )
        self._patterns = self._load_patterns()

    def parse(self, text: str) -> Intent:
        """Parse a transcript into a recognized intent."""
        raw_text = (text or "").strip()
        if not raw_text:
            return self._unknown(raw_text)

        regex_match = self._parse_with_regex(raw_text)
        if regex_match is not None:
            intent, confidence = regex_match
            if confidence >= self._threshold:
                return intent

        keyword_match = self._parse_with_keywords(raw_text)
        if keyword_match is not None:
            intent, confidence = keyword_match
            if confidence >= self._threshold:
                return intent

        return self._unknown(raw_text)

    def category_for_intent(self, intent_name: str) -> IntentCategory:
        """Resolve dispatcher category from an intent name."""
        return _intent_category(intent_name)

    def _parse_with_regex(self, text: str) -> tuple[Intent, float] | None:
        lowered = text.lower()
        for pattern in self._patterns:
            match = pattern.regex.match(lowered)
            if not match:
                continue

            slots = [
                IntentSlot(name=name, value=value.strip())
                for name, value in match.groupdict().items()
                if value and value.strip()
            ]
            intent = Intent(
                name=pattern.intent_name,
                slots=slots,
                confidence=0.95,
                raw_text=text,
            )
            return intent, intent.confidence
        return None

    def _parse_with_keywords(self, text: str) -> tuple[Intent, float] | None:
        lowered = text.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                intent = Intent(
                    name=_default_intent_name(category),
                    confidence=0.55,
                    raw_text=text,
                )
                return intent, intent.confidence
        return None

    def _load_patterns(self) -> list[CompiledPattern]:
        source = self._load_sentences_from_file()
        if not source:
            source = DEFAULT_SENTENCES

        patterns: list[CompiledPattern] = []
        for intent_name, raw_patterns in source.items():
            category = _intent_category(intent_name)
            for raw_pattern in raw_patterns:
                compiled = _compile_pattern(raw_pattern)
                if compiled is None:
                    continue
                patterns.append(
                    CompiledPattern(
                        intent_name=intent_name,
                        category=category,
                        regex=compiled,
                        specificity=_specificity(raw_pattern),
                    )
                )
        return sorted(
            patterns,
            key=lambda item: item.specificity,
            reverse=True,
        )

    def _load_sentences_from_file(self) -> dict[str, list[str]]:
        if not self._sentences_path.exists():
            return {}

        parser = _SentencesConfigParser(
            allow_no_value=True,
            interpolation=None,
            strict=False,
        )
        parser.read(self._sentences_path, encoding="utf-8")

        results: dict[str, list[str]] = {}
        for section in parser.sections():
            keys = parser[section].keys()
            patterns = [line.strip() for line in keys if line.strip()]
            if patterns:
                results[section.strip()] = patterns
        return results

    @staticmethod
    def _unknown(raw_text: str) -> Intent:
        return Intent(
            name="unknown",
            confidence=0.0,
            raw_text=raw_text,
        )


def _compile_pattern(raw_pattern: str) -> re.Pattern[str] | None:
    transformed = _replace_slot_tokens(raw_pattern.strip().lower())
    transformed = re.sub(r"\s+", r"\\s+", transformed)

    try:
        return re.compile(rf"^{transformed}$", re.IGNORECASE)
    except re.error:
        return None


def _replace_slot_tokens(pattern: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        slot_name = match.group(1)
        return rf"(?P<{slot_name}>[a-zA-Z0-9_\-\s:]+?)"

    return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", _replace, pattern)


class _SentencesConfigParser(configparser.ConfigParser):
    def optionxform(self, optionstr: str) -> str:
        return optionstr


def _specificity(pattern: str) -> int:
    cleaned = re.sub(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}", "", pattern)
    return len(re.sub(r"\s+", "", cleaned))


def _intent_category(intent_name: str) -> IntentCategory:
    if intent_name in INTENT_CATEGORY_MAP:
        return INTENT_CATEGORY_MAP[intent_name]

    lowered = intent_name.lower()
    if "calendar" in lowered:
        return IntentCategory.CALENDAR
    if "task" in lowered or "todo" in lowered or "list" in lowered:
        return IntentCategory.TASKS
    if "weather" in lowered or "forecast" in lowered:
        return IntentCategory.WEATHER
    if "timer" in lowered or "alarm" in lowered:
        return IntentCategory.TIMERS
    if "music" in lowered or "song" in lowered or "volume" in lowered:
        return IntentCategory.MUSIC
    if (
        "scene" in lowered
        or "device" in lowered
        or "light" in lowered
        or "smarthome" in lowered
    ):
        return IntentCategory.SMARTHOME
    if "system" in lowered or "photo" in lowered or "sleep" in lowered:
        return IntentCategory.SYSTEM
    return IntentCategory.UNKNOWN


def _default_intent_name(category: IntentCategory) -> str:
    defaults = {
        IntentCategory.CALENDAR: "get_calendar",
        IntentCategory.TASKS: "get_tasks",
        IntentCategory.WEATHER: "get_weather",
        IntentCategory.TIMERS: "set_timer",
        IntentCategory.MUSIC: "play_music",
        IntentCategory.SMARTHOME: "turn_device",
        IntentCategory.SYSTEM: "show_photo_frame",
    }
    return defaults.get(category, "unknown")


def iter_supported_intents() -> Iterable[str]:
    """Expose known intent names for introspection/tests."""
    return tuple(INTENT_CATEGORY_MAP.keys())
