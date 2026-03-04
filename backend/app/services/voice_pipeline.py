"""End-to-end voice pipeline orchestration service."""

from __future__ import annotations


class VoicePipeline:
    """Run STT -> NLU -> dispatch -> TTS for captured voice audio."""

    def __init__(
        self,
        wake_word_service,
        stt_service,
        nlu_service,
        dispatch_service,
        tts_service,
    ) -> None:
        self.wake_word_service = wake_word_service
        self.stt_service = stt_service
        self.nlu_service = nlu_service
        self.dispatch_service = dispatch_service
        self.tts_service = tts_service

    async def process_audio(self, audio_bytes: bytes) -> str:
        """Wake word already detected; run STT -> NLU -> dispatch -> TTS."""
        transcript = await self.stt_service.transcribe(audio_bytes)
        intent = self.nlu_service.parse(transcript)
        response = await self.dispatch_service.dispatch(intent)
        await self.tts_service.speak(response)
        return response
