"""Voice intent handler for music controls."""

from __future__ import annotations

from app.schemas.intent import Intent
from app.services.music import MopidyMusicService

_VOLUME_STEP = 10


def _get_slot(intent: Intent, name: str) -> str | None:
    for slot in intent.slots:
        if slot.name == name and slot.value:
            return slot.value.strip()
    return None


class MusicIntentHandler:
    """Handle music intents and return TTS-friendly responses."""

    def __init__(self, music_service: MopidyMusicService) -> None:
        self._music = music_service

    async def handle(self, intent: Intent) -> str:
        intent_name = (intent.name or "").lower()

        if intent_name in {"play_music", "resume_music"}:
            await self._music.play()
            return "Playing music."

        if intent_name == "pause_music":
            await self._music.pause()
            return "Paused."

        if intent_name in {"next_song", "skip_track", "next_track"}:
            await self._music.next_track()
            return "Skipping to the next track."

        if intent_name in {"previous_song", "previous_track"}:
            await self._music.previous_track()
            return "Going back to the previous track."

        if intent_name in {"set_shuffle", "shuffle_on", "shuffle_off"}:
            enabled = intent_name != "shuffle_off"
            await self._music.set_shuffle(enabled)
            return "Shuffle is on." if enabled else "Shuffle is off."

        if intent_name == "set_volume":
            return await self._handle_volume_intent(intent)

        return "I'm not sure how to handle that music request."

    async def _handle_volume_intent(self, intent: Intent) -> str:
        raw_text = (intent.raw_text or "").lower()
        level_slot = _get_slot(intent, "level")

        if level_slot:
            try:
                level = int(level_slot)
            except ValueError:
                return "I need a volume number between 0 and 100."

            clamped = max(0, min(100, level))
            await self._music.set_volume(clamped)
            return f"Volume set to {clamped} percent."

        current = await self._music.get_volume()
        if "down" in raw_text:
            updated = max(0, current - _VOLUME_STEP)
            await self._music.set_volume(updated)
            return f"Volume down to {updated} percent."

        updated = min(100, current + _VOLUME_STEP)
        await self._music.set_volume(updated)
        return f"Volume up to {updated} percent."
