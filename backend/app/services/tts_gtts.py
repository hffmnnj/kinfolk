"""gTTS backend — network-based text-to-speech via Google Translate."""

from __future__ import annotations

import io
import logging
import subprocess
import tempfile
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class GTTSBackend:
    """Synthesise speech using the ``gTTS`` Python package.

    Requires network access.  Output is converted from MP3 to WAV
    so that all TTS backends return a uniform audio format.
    """

    def __init__(
        self,
        lang: str = "en",
        slow: bool = False,
    ) -> None:
        self._lang = lang
        self._slow = slow

    @property
    def available(self) -> bool:
        """Return *True* when the gTTS package can be imported."""
        try:
            import gtts  # noqa: F401

            return True
        except ImportError:
            return False

    async def synthesize(self, text: str) -> bytes:
        """Convert *text* to WAV audio bytes.

        Raises ``RuntimeError`` on network errors or missing
        dependencies.
        """
        try:
            from gtts import gTTS
        except ImportError as exc:
            msg = "gtts not installed"
            raise RuntimeError(msg) from exc

        try:
            tts = gTTS(
                text=text,
                lang=self._lang,
                slow=self._slow,
            )
        except Exception as exc:
            raise RuntimeError(f"gTTS initialisation failed: {exc}") from exc

        mp3_buf = io.BytesIO()
        try:
            tts.write_to_fp(mp3_buf)
        except Exception as exc:
            raise RuntimeError(
                f"gTTS synthesis failed (network error?): {exc}"
            ) from exc

        mp3_bytes = mp3_buf.getvalue()
        return self._mp3_to_wav(mp3_bytes)

    @staticmethod
    def _mp3_to_wav(mp3_data: bytes) -> bytes:
        """Convert MP3 bytes to WAV via ffmpeg subprocess.

        Falls back to returning raw MP3 when no converter
        is available.
        """
        with tempfile.NamedTemporaryFile(
            suffix=".mp3",
            delete=False,
        ) as mp3_tmp:
            mp3_path = Path(mp3_tmp.name)
            mp3_tmp.write(mp3_data)

        wav_path = mp3_path.with_suffix(".wav")

        try:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(mp3_path),
                    "-ar",
                    "22050",
                    "-ac",
                    "1",
                    str(wav_path),
                ],
                capture_output=True,
                timeout=30,
                check=False,
            )
            if proc.returncode != 0:
                LOGGER.warning(
                    "ffmpeg failed (rc=%d); returning raw MP3",
                    proc.returncode,
                )
                return mp3_data

            return wav_path.read_bytes()
        except FileNotFoundError:
            LOGGER.warning(
                "ffmpeg not found on $PATH; returning raw MP3 bytes",
            )
            return mp3_data
        finally:
            mp3_path.unlink(missing_ok=True)
            wav_path.unlink(missing_ok=True)
