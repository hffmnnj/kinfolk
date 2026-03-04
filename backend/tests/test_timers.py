"""Tests for timer service, router, and intent handler."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.timer import Timer
from app.schemas.intent import Intent, IntentSlot
from app.services.intent_handlers.timer_handler import (
    TimerIntentHandler,
    _format_duration,
    _parse_duration_seconds,
)
from app.services.timers import TimerService


# ---------------------------------------------------------------------------
# Fixtures — in-memory SQLite for isolation
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite database with the timers table."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def db_factory(db_session):
    """Return a factory that always yields the same test session."""

    def _factory():
        return db_session

    return _factory


@pytest.fixture()
def timer_service(db_factory):
    """TimerService wired to the in-memory DB, no TTS."""
    return TimerService(db_factory=db_factory, tts_service=None)


@pytest.fixture()
def timer_handler(timer_service):
    """TimerIntentHandler wired to the test TimerService."""
    return TimerIntentHandler(timer_service=timer_service)


# ---------------------------------------------------------------------------
# TimerService — creation and countdown
# ---------------------------------------------------------------------------


class TestTimerService:
    def test_set_timer_creates_record(self, timer_service):
        timer = timer_service.set_timer(name="pasta", duration_seconds=600)

        assert timer.id is not None
        assert timer.name == "pasta"
        assert timer.duration_seconds == 600
        assert timer.completed is False
        assert timer.cancelled is False

    def test_set_timer_fire_at_in_future(self, timer_service):
        timer = timer_service.set_timer(name="eggs", duration_seconds=300)
        now = datetime.now(timezone.utc)

        fire_at = timer.fire_at
        # SQLite returns naive datetimes — treat as UTC for comparison
        if fire_at.tzinfo is None:
            fire_at = fire_at.replace(tzinfo=timezone.utc)
        assert fire_at > now

    def test_remaining_seconds_positive(self, timer_service):
        timer = timer_service.set_timer(name="tea", duration_seconds=120)
        remaining = TimerService.remaining_seconds(timer)

        assert 0 < remaining <= 120

    def test_set_alarm_at_specific_time(self, timer_service):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        alarm = timer_service.set_alarm(name="morning", fire_at=future)

        assert alarm.name == "morning"
        # SQLite strips timezone — compare as naive UTC
        fire_at = alarm.fire_at
        if fire_at.tzinfo is None:
            fire_at = fire_at.replace(tzinfo=timezone.utc)
        # Allow 1-second tolerance for rounding
        assert abs((fire_at - future).total_seconds()) < 1
        assert alarm.completed is False

    def test_get_timers_returns_active_only(self, timer_service):
        timer_service.set_timer(name="active", duration_seconds=300)
        t2 = timer_service.set_timer(name="done", duration_seconds=1)

        # Manually mark one as completed
        timer_service.cancel_timer(t2.id)

        active = timer_service.get_timers()
        assert len(active) == 1
        assert active[0].name == "active"

    def test_cancel_timer_by_id(self, timer_service):
        timer = timer_service.set_timer(name="cancel-me", duration_seconds=60)
        result = timer_service.cancel_timer(timer.id)

        assert result is True
        assert len(timer_service.get_timers()) == 0

    def test_cancel_nonexistent_timer(self, timer_service):
        result = timer_service.cancel_timer(str(uuid.uuid4()))
        assert result is False

    def test_cancel_timer_by_name(self, timer_service):
        timer_service.set_timer(name="cookies", duration_seconds=600)
        timer_service.set_timer(name="pasta", duration_seconds=300)

        count = timer_service.cancel_timer_by_name("cookies")
        assert count == 1
        assert len(timer_service.get_timers()) == 1

    def test_cancel_all_timers(self, timer_service):
        timer_service.set_timer(name="a", duration_seconds=60)
        timer_service.set_timer(name="b", duration_seconds=120)

        count = timer_service.cancel_all_timers()
        assert count == 2
        assert len(timer_service.get_timers()) == 0

    def test_multiple_concurrent_timers(self, timer_service):
        timer_service.set_timer(name="first", duration_seconds=60)
        timer_service.set_timer(name="second", duration_seconds=120)
        timer_service.set_timer(name="third", duration_seconds=180)

        active = timer_service.get_timers()
        assert len(active) == 3


# ---------------------------------------------------------------------------
# Timer persistence
# ---------------------------------------------------------------------------


class TestTimerPersistence:
    def test_timer_persisted_to_db(self, db_session, db_factory):
        service = TimerService(db_factory=db_factory)
        service.set_timer(name="persist-test", duration_seconds=60)

        # Query directly from DB
        count = db_session.query(Timer).count()
        assert count == 1

        row = db_session.query(Timer).first()
        assert row.name == "persist-test"

    def test_cancelled_timer_persisted(self, db_session, db_factory):
        service = TimerService(db_factory=db_factory)
        timer = service.set_timer(name="cancel-persist", duration_seconds=60)
        service.cancel_timer(timer.id)

        row = db_session.query(Timer).filter(Timer.id == timer.id).first()
        assert row.cancelled is True


# ---------------------------------------------------------------------------
# Background monitor
# ---------------------------------------------------------------------------


class TestTimerMonitor:
    @pytest.mark.asyncio
    async def test_check_expired_marks_completed(self, db_factory):
        tts_mock = AsyncMock()
        tts_mock.speak = AsyncMock()
        service = TimerService(db_factory=db_factory, tts_service=tts_mock)

        # Create a timer that's already expired
        timer = service.set_timer(name="expired", duration_seconds=0)

        await service._check_expired()

        # Verify it was marked completed
        timers = service.get_timers()
        assert len(timers) == 0  # No active timers

        # Verify TTS was called
        tts_mock.speak.assert_called_once()
        assert "expired" in tts_mock.speak.call_args[0][0]

    @pytest.mark.asyncio
    async def test_check_expired_no_tts_when_none(self, db_factory):
        service = TimerService(db_factory=db_factory, tts_service=None)
        service.set_timer(name="no-tts", duration_seconds=0)

        # Should not raise even without TTS
        await service._check_expired()


# ---------------------------------------------------------------------------
# Duration parsing
# ---------------------------------------------------------------------------


class TestDurationParsing:
    def test_parse_five_minutes(self):
        assert _parse_duration_seconds("five minutes") == 300

    def test_parse_10_minutes(self):
        assert _parse_duration_seconds("10 minutes") == 600

    def test_parse_one_hour(self):
        assert _parse_duration_seconds("one hour") == 3600

    def test_parse_90_seconds(self):
        assert _parse_duration_seconds("90 seconds") == 90

    def test_parse_a_minute(self):
        assert _parse_duration_seconds("a minute") == 60

    def test_parse_fifteen_minutes(self):
        assert _parse_duration_seconds("fifteen minutes") == 900

    def test_parse_bare_number_assumes_minutes(self):
        assert _parse_duration_seconds("5") == 300

    def test_parse_empty_returns_none(self):
        assert _parse_duration_seconds("") is None

    def test_parse_nonsense_returns_none(self):
        assert _parse_duration_seconds("banana") is None

    def test_parse_thirty_seconds(self):
        assert _parse_duration_seconds("thirty seconds") == 30


# ---------------------------------------------------------------------------
# Duration formatting
# ---------------------------------------------------------------------------


class TestDurationFormatting:
    def test_format_minutes(self):
        assert _format_duration(300) == "5 minutes"

    def test_format_hour_and_minutes(self):
        assert _format_duration(3900) == "1 hour and 5 minutes"

    def test_format_seconds_only(self):
        assert _format_duration(45) == "45 seconds"

    def test_format_zero(self):
        assert _format_duration(0) == "0 seconds"


# ---------------------------------------------------------------------------
# Intent handler
# ---------------------------------------------------------------------------


class TestTimerIntentHandler:
    @pytest.mark.asyncio
    async def test_set_timer_intent(self, timer_handler, timer_service):
        intent = Intent(
            name="set_timer",
            slots=[
                IntentSlot(name="duration", value="five minutes"),
                IntentSlot(name="name", value="cookies"),
            ],
        )

        response = await timer_handler.handle(intent)

        assert "cookies" in response.lower()
        assert "5 minutes" in response.lower()
        assert len(timer_service.get_timers()) == 1

    @pytest.mark.asyncio
    async def test_query_timer_intent(self, timer_handler, timer_service):
        timer_service.set_timer(name="pasta", duration_seconds=600)

        intent = Intent(name="query_timer", slots=[])
        response = await timer_handler.handle(intent)

        assert "pasta" in response.lower()
        assert "remaining" in response.lower()

    @pytest.mark.asyncio
    async def test_cancel_timer_intent(self, timer_handler, timer_service):
        timer_service.set_timer(name="eggs", duration_seconds=300)

        intent = Intent(
            name="cancel_timer",
            slots=[IntentSlot(name="name", value="eggs")],
        )
        response = await timer_handler.handle(intent)

        assert "cancelled" in response.lower()
        assert len(timer_service.get_timers()) == 0

    @pytest.mark.asyncio
    async def test_cancel_all_timers_intent(self, timer_handler, timer_service):
        timer_service.set_timer(name="a", duration_seconds=60)
        timer_service.set_timer(name="b", duration_seconds=120)

        intent = Intent(
            name="cancel_timer",
            slots=[IntentSlot(name="name", value="all")],
        )
        response = await timer_handler.handle(intent)

        assert "cancelled" in response.lower()
        assert "2" in response

    @pytest.mark.asyncio
    async def test_set_timer_missing_duration(self, timer_handler):
        intent = Intent(name="set_timer", slots=[])
        response = await timer_handler.handle(intent)

        assert "how long" in response.lower()

    @pytest.mark.asyncio
    async def test_query_no_active_timers(self, timer_handler):
        intent = Intent(name="query_timer", slots=[])
        response = await timer_handler.handle(intent)

        assert "don't have" in response.lower()
