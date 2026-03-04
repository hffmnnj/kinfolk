"""Timer and alarm service with background expiry monitoring.

Manages named timers and alarms persisted to the database.  A
background asyncio task checks for expired timers every second and
fires a TTS alert when one completes.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy.orm import Session

from app.models.timer import Timer

LOGGER = logging.getLogger(__name__)


class TimerService:
    """Concurrent named timers and alarms with DB persistence."""

    def __init__(
        self,
        db_factory: Callable[[], Session],
        tts_service: Optional[object] = None,
    ) -> None:
        self._db_factory = db_factory
        self._tts = tts_service
        self._monitor_task: Optional[asyncio.Task[None]] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the background expiry monitor."""
        if self._monitor_task is None:
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            LOGGER.info("Timer expiry monitor started")

    async def stop(self) -> None:
        """Cancel the background monitor."""
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            LOGGER.info("Timer expiry monitor stopped")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_timer(
        self,
        name: str,
        duration_seconds: int,
        user_id: Optional[str] = None,
    ) -> Timer:
        """Create a named countdown timer."""
        now = datetime.now(timezone.utc)
        fire_at = now + timedelta(seconds=duration_seconds)

        timer = Timer(
            id=str(uuid.uuid4()),
            name=name,
            duration_seconds=duration_seconds,
            started_at=now,
            fire_at=fire_at,
            user_id=user_id,
        )

        db: Session = self._db_factory()
        try:
            db.add(timer)
            db.commit()
            db.refresh(timer)
        finally:
            db.close()

        LOGGER.info("Timer '%s' set for %d seconds", name, duration_seconds)
        return timer

    def set_alarm(
        self,
        name: str,
        fire_at: datetime,
        user_id: Optional[str] = None,
    ) -> Timer:
        """Create a named alarm that fires at a specific time."""
        now = datetime.now(timezone.utc)
        duration = max(0, int((fire_at - now).total_seconds()))

        timer = Timer(
            id=str(uuid.uuid4()),
            name=name,
            duration_seconds=duration,
            started_at=now,
            fire_at=fire_at,
            user_id=user_id,
        )

        db: Session = self._db_factory()
        try:
            db.add(timer)
            db.commit()
            db.refresh(timer)
        finally:
            db.close()

        LOGGER.info("Alarm '%s' set for %s", name, fire_at.isoformat())
        return timer

    def get_timers(self, include_done: bool = False) -> list[Timer]:
        """Return active (or all) timers ordered by fire time."""
        db: Session = self._db_factory()
        try:
            query = db.query(Timer)
            if not include_done:
                query = query.filter(
                    Timer.completed.is_(False),
                    Timer.cancelled.is_(False),
                )
            timers = query.order_by(Timer.fire_at).all()
            # Detach from session so callers can use them freely
            db.expunge_all()
            return timers
        finally:
            db.close()

    def cancel_timer(self, timer_id: str) -> bool:
        """Cancel a timer by ID.  Returns True if found and cancelled."""
        db: Session = self._db_factory()
        try:
            timer = db.query(Timer).filter(Timer.id == timer_id).first()
            if timer is None or timer.completed or timer.cancelled:
                return False
            timer.cancelled = True
            db.commit()
            LOGGER.info("Timer '%s' cancelled", timer.name)
            return True
        finally:
            db.close()

    def cancel_timer_by_name(self, name: str) -> int:
        """Cancel all active timers matching *name* (case-insensitive).

        Returns the number of timers cancelled.
        """
        db: Session = self._db_factory()
        try:
            timers = (
                db.query(Timer)
                .filter(
                    Timer.completed.is_(False),
                    Timer.cancelled.is_(False),
                )
                .all()
            )
            count = 0
            search = name.lower()
            for timer in timers:
                if search in timer.name.lower():
                    timer.cancelled = True
                    count += 1
            if count:
                db.commit()
            return count
        finally:
            db.close()

    def cancel_all_timers(self) -> int:
        """Cancel every active timer.  Returns count cancelled."""
        db: Session = self._db_factory()
        try:
            timers = (
                db.query(Timer)
                .filter(
                    Timer.completed.is_(False),
                    Timer.cancelled.is_(False),
                )
                .all()
            )
            count = len(timers)
            for timer in timers:
                timer.cancelled = True
            if count:
                db.commit()
            return count
        finally:
            db.close()

    @staticmethod
    def remaining_seconds(timer: Timer) -> int:
        """Seconds remaining until *timer* fires (0 if expired)."""
        now = datetime.now(timezone.utc)
        fire_at = timer.fire_at
        # SQLite stores naive datetimes — treat them as UTC
        if fire_at.tzinfo is None:
            fire_at = fire_at.replace(tzinfo=timezone.utc)
        delta = (fire_at - now).total_seconds()
        return max(0, int(delta))

    # ------------------------------------------------------------------
    # Background monitor
    # ------------------------------------------------------------------

    async def _monitor_loop(self) -> None:
        """Check for expired timers every second."""
        while True:
            try:
                await self._check_expired()
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception("Error in timer monitor loop")
            await asyncio.sleep(1)

    async def _check_expired(self) -> None:
        """Mark expired timers as completed and fire TTS alerts."""
        now = datetime.now(timezone.utc)
        db: Session = self._db_factory()
        try:
            expired = (
                db.query(Timer)
                .filter(
                    Timer.completed.is_(False),
                    Timer.cancelled.is_(False),
                    Timer.fire_at <= now,
                )
                .all()
            )
            for timer in expired:
                timer.completed = True
                LOGGER.info("Timer '%s' expired", timer.name)
                await self._fire_alert(timer)
            if expired:
                db.commit()
        finally:
            db.close()

    async def _fire_alert(self, timer: Timer) -> None:
        """Announce timer completion via TTS."""
        if self._tts is None:
            return
        message = f"Your {timer.name} timer is done."
        try:
            await self._tts.speak(message)
        except Exception:
            LOGGER.exception("TTS alert failed for timer '%s'", timer.name)
