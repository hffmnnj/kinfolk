"""Tests for rule-based NLU intent parsing."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.schemas.intent import IntentCategory
from app.services.nlu import NLUService


def _settings(threshold: float = 0.5) -> SimpleNamespace:
    sentences_path = Path(__file__).resolve().parents[1] / "rhasspy" / "sentences.ini"
    return SimpleNamespace(
        nlu_confidence_threshold=threshold,
        sentences_ini_path=str(sentences_path),
    )


@pytest.mark.parametrize(
    ("utterance", "expected_category"),
    [
        ("what's on my calendar", IntentCategory.CALENDAR),
        ("add milk to my shopping list", IntentCategory.TASKS),
        ("what's the weather", IntentCategory.WEATHER),
        ("set a timer for ten minutes", IntentCategory.TIMERS),
        ("play miles davis", IntentCategory.MUSIC),
        ("turn on kitchen lights", IntentCategory.SMARTHOME),
        ("show photo frame", IntentCategory.SYSTEM),
    ],
)
def test_parse_recognizes_all_intent_categories(
    utterance: str,
    expected_category: IntentCategory,
):
    service = NLUService(settings=_settings())

    intent = service.parse(utterance)

    assert service.category_for_intent(intent.name) == expected_category
    assert intent.name != "unknown"
    assert intent.confidence >= 0.5


def test_parse_extracts_timer_duration_slot():
    service = NLUService(settings=_settings())

    intent = service.parse("set a timer for 25 minutes")
    slots = {slot.name: slot.value for slot in intent.slots}

    assert intent.name == "set_timer"
    assert slots["duration"] == "25 minutes"


def test_parse_extracts_task_slots():
    service = NLUService(settings=_settings())

    intent = service.parse("add milk to my shopping list")
    slots = {slot.name: slot.value for slot in intent.slots}

    assert intent.name == "add_task"
    assert slots["item"] == "milk"
    assert slots["list_name"] == "shopping"


def test_parse_returns_unknown_for_unrecognized_utterance():
    service = NLUService(settings=_settings())

    intent = service.parse("abracadabra speak friend and enter")

    assert intent.name == "unknown"
    assert intent.confidence == 0.0


def test_parse_applies_confidence_threshold_filtering():
    service = NLUService(settings=_settings(threshold=0.8))

    # "weather" keyword triggers low-confidence keyword fallback (0.55)
    intent = service.parse("weather outside")

    assert intent.name == "unknown"
    assert intent.confidence == 0.0
