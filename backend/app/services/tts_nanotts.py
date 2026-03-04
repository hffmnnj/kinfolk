"""NanoTTS backend — fully offline TTS via nanotts binary."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class NanoTTSBackend:
    """Synthesise speech using the ``nanotts`` CLI tool.

    Falls back gracefully when the binary is not installed.
    """

    def __init__(
        self,
        lang: str = "en-US",
        speed: float = 1.0,
        volume: float = 0.8,
    ) -> None:
        self._lang = lang
        self._speed = speed
        self._volume = volume
        self._binary = shutil.which("nanotts")

    @property
    def available(self) -> bool:
        """Return *True* when nanotts is on ``$PATH``."""
        return self._binary is not None

    async def synthesize(self, text: str) -> bytes:
        """Convert *text* to WAV audio bytes.

        Raises ``RuntimeError`` when the nanotts binary is
        missing or the subprocess exits with a non-zero code.
        """
        if not self._binary:
            raise RuntimeError(
                "nanotts binary not found on $PATH — "
                "install it or switch to the gtts engine"
            )

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        ) as tmp:
            out_path = Path(tmp.name)

        try:
            cmd = [
                self._binary,
                "-l",
                self._lang,
                "-o",
                str(out_path),
                "--speed",
                str(self._speed),
                "--volume",
                str(self._volume),
            ]
            proc = subprocess.run(
                cmd,
                input=text,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if proc.returncode != 0:
                LOGGER.error(
                    "nanotts failed (rc=%d): %s",
                    proc.returncode,
                    proc.stderr.strip(),
                )
                msg = f"nanotts exited with code {proc.returncode}"
                raise RuntimeError(msg)

            return out_path.read_bytes()
        finally:
            out_path.unlink(missing_ok=True)
