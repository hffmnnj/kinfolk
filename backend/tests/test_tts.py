"""Tests for Text-to-Speech service and backends."""

from __future__ import annotations

import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.tts import TTSService
from app.services.tts_nanotts import NanoTTSBackend
from app.services.tts_gtts import GTTSBackend


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides):
    """Return a minimal settings-like object for TTSService."""
    defaults = {
        "tts_engine": "nanotts",
        "tts_speed": 1.0,
        "tts_volume": 0.8,
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


class _FakeBackend:
    """Stub backend that returns deterministic audio bytes."""

    def __init__(self, data: bytes = b"RIFF-fake-wav", available: bool = True):
        self._data = data
        self.available = available
        self.last_text: str | None = None

    async def synthesize(self, text: str) -> bytes:
        self.last_text = text
        return self._data


# ---------------------------------------------------------------------------
# TTSService — delegation and engine selection
# ---------------------------------------------------------------------------


class TestTTSServiceDelegation:
    """TTSService delegates to the correct backend based on config."""

    @pytest.mark.asyncio
    async def test_delegates_to_nanotts_when_configured(self):
        backend = _FakeBackend()
        svc = TTSService(
            _make_settings(tts_engine="nanotts"),
            backend_override=backend,
        )
        assert svc.engine == "nanotts"
        result = await svc.synthesize("hello")
        assert result == b"RIFF-fake-wav"
        assert backend.last_text == "hello"

    @pytest.mark.asyncio
    async def test_delegates_to_gtts_when_configured(self):
        backend = _FakeBackend()
        svc = TTSService(
            _make_settings(tts_engine="gtts"),
            backend_override=backend,
        )
        assert svc.engine == "gtts"
        result = await svc.synthesize("world")
        assert result == b"RIFF-fake-wav"
        assert backend.last_text == "world"

    @pytest.mark.asyncio
    async def test_builds_nanotts_backend_by_default(self):
        svc = TTSService(_make_settings(tts_engine="nanotts"))
        assert svc.engine == "nanotts"
        assert isinstance(svc._backend, NanoTTSBackend)

    @pytest.mark.asyncio
    async def test_builds_gtts_backend_when_configured(self):
        svc = TTSService(_make_settings(tts_engine="gtts"))
        assert svc.engine == "gtts"
        assert isinstance(svc._backend, GTTSBackend)


# ---------------------------------------------------------------------------
# TTSService — synthesize behaviour
# ---------------------------------------------------------------------------


class TestTTSServiceSynthesize:
    """synthesize() returns bytes and handles edge cases."""

    @pytest.mark.asyncio
    async def test_returns_bytes(self):
        backend = _FakeBackend(data=b"\x00\x01\x02")
        svc = TTSService(
            _make_settings(),
            backend_override=backend,
        )
        result = await svc.synthesize("test")
        assert isinstance(result, bytes)
        assert result == b"\x00\x01\x02"

    @pytest.mark.asyncio
    async def test_empty_text_returns_empty_bytes(self):
        backend = _FakeBackend()
        svc = TTSService(
            _make_settings(),
            backend_override=backend,
        )
        result = await svc.synthesize("")
        assert result == b""
        assert backend.last_text is None  # backend not called

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_empty_bytes(self):
        backend = _FakeBackend()
        svc = TTSService(
            _make_settings(),
            backend_override=backend,
        )
        result = await svc.synthesize("   ")
        assert result == b""


# ---------------------------------------------------------------------------
# TTSService — speak behaviour
# ---------------------------------------------------------------------------


class TestTTSServiceSpeak:
    """speak() synthesises and plays audio."""

    @pytest.mark.asyncio
    async def test_speak_calls_playback_with_audio(self):
        playback = AsyncMock()
        backend = _FakeBackend(data=b"wav-data")
        svc = TTSService(
            _make_settings(),
            backend_override=backend,
            playback_fn=playback,
        )
        await svc.speak("hello world")
        playback.assert_awaited_once_with(b"wav-data")

    @pytest.mark.asyncio
    async def test_speak_skips_playback_for_empty_text(self):
        playback = AsyncMock()
        backend = _FakeBackend()
        svc = TTSService(
            _make_settings(),
            backend_override=backend,
            playback_fn=playback,
        )
        await svc.speak("")
        playback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_speak_skips_playback_when_no_audio_produced(self):
        playback = AsyncMock()
        backend = _FakeBackend(data=b"")
        svc = TTSService(
            _make_settings(),
            backend_override=backend,
            playback_fn=playback,
        )
        await svc.speak("something")
        playback.assert_not_awaited()


# ---------------------------------------------------------------------------
# TTSService — available property
# ---------------------------------------------------------------------------


class TestTTSServiceAvailable:
    """available property reflects backend state."""

    def test_available_true_when_backend_available(self):
        backend = _FakeBackend(available=True)
        svc = TTSService(
            _make_settings(),
            backend_override=backend,
        )
        assert svc.available is True

    def test_available_false_when_backend_unavailable(self):
        backend = _FakeBackend(available=False)
        svc = TTSService(
            _make_settings(),
            backend_override=backend,
        )
        assert svc.available is False


# ---------------------------------------------------------------------------
# NanoTTSBackend
# ---------------------------------------------------------------------------


class TestNanoTTSBackend:
    """NanoTTS backend tests with mocked subprocess."""

    def test_available_when_binary_found(self):
        with patch(
            "app.services.tts_nanotts.shutil.which", return_value="/usr/bin/nanotts"
        ):
            backend = NanoTTSBackend()
            assert backend.available is True

    def test_unavailable_when_binary_missing(self):
        with patch("app.services.tts_nanotts.shutil.which", return_value=None):
            backend = NanoTTSBackend()
            assert backend.available is False

    @pytest.mark.asyncio
    async def test_synthesize_raises_when_binary_missing(self):
        with patch("app.services.tts_nanotts.shutil.which", return_value=None):
            backend = NanoTTSBackend()
            with pytest.raises(RuntimeError, match="nanotts binary not found"):
                await backend.synthesize("hello")

    @pytest.mark.asyncio
    async def test_synthesize_returns_wav_bytes(self):
        fake_wav = b"RIFF\x00\x00\x00\x00WAVEfmt "

        with patch(
            "app.services.tts_nanotts.shutil.which", return_value="/usr/bin/nanotts"
        ):
            backend = NanoTTSBackend(speed=1.2, volume=0.9)

        with (
            patch("app.services.tts_nanotts.subprocess.run") as mock_run,
            patch("app.services.tts_nanotts.Path.read_bytes", return_value=fake_wav),
            patch("app.services.tts_nanotts.Path.unlink"),
        ):
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            result = await backend.synthesize("test speech")

        assert result == fake_wav
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "/usr/bin/nanotts"
        assert "-l" in cmd
        assert "en-US" in cmd
        assert "--speed" in cmd
        assert "1.2" in cmd
        assert "--volume" in cmd
        assert "0.9" in cmd

    @pytest.mark.asyncio
    async def test_synthesize_raises_on_nonzero_exit(self):
        with patch(
            "app.services.tts_nanotts.shutil.which", return_value="/usr/bin/nanotts"
        ):
            backend = NanoTTSBackend()

        with (
            patch("app.services.tts_nanotts.subprocess.run") as mock_run,
            patch("app.services.tts_nanotts.Path.unlink"),
        ):
            mock_run.return_value = MagicMock(returncode=1, stderr="error: bad input")
            with pytest.raises(RuntimeError, match="exited with code 1"):
                await backend.synthesize("fail")


# ---------------------------------------------------------------------------
# GTTSBackend
# ---------------------------------------------------------------------------


class TestGTTSBackend:
    """gTTS backend tests with mocked gtts package."""

    def test_available_when_gtts_importable(self):
        with patch.dict("sys.modules", {"gtts": MagicMock()}):
            backend = GTTSBackend()
            assert backend.available is True

    def test_unavailable_when_gtts_not_installed(self):
        with patch.dict("sys.modules", {"gtts": None}):
            backend = GTTSBackend()
            assert backend.available is False

    @pytest.mark.asyncio
    async def test_synthesize_raises_when_gtts_missing(self):
        with patch.dict("sys.modules", {"gtts": None}):
            backend = GTTSBackend()
            with pytest.raises(RuntimeError, match="gtts not installed"):
                await backend.synthesize("hello")

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio_bytes(self):
        fake_mp3 = b"\xff\xfb\x90\x00"  # MP3 header bytes

        mock_gtts_instance = MagicMock()
        mock_gtts_instance.write_to_fp.side_effect = lambda fp: fp.write(fake_mp3)
        mock_gtts_class = MagicMock(return_value=mock_gtts_instance)
        mock_gtts_module = MagicMock()
        mock_gtts_module.gTTS = mock_gtts_class

        with patch.dict("sys.modules", {"gtts": mock_gtts_module}):
            backend = GTTSBackend(lang="en", slow=False)

            # Mock _mp3_to_wav to return known bytes
            with patch.object(
                GTTSBackend, "_mp3_to_wav", return_value=b"wav-converted"
            ):
                result = await backend.synthesize("test text")

        assert result == b"wav-converted"
        mock_gtts_class.assert_called_once_with(text="test text", lang="en", slow=False)

    @pytest.mark.asyncio
    async def test_synthesize_raises_on_network_error(self):
        mock_gtts_instance = MagicMock()
        mock_gtts_instance.write_to_fp.side_effect = Exception("Network unreachable")
        mock_gtts_class = MagicMock(return_value=mock_gtts_instance)
        mock_gtts_module = MagicMock()
        mock_gtts_module.gTTS = mock_gtts_class

        with patch.dict("sys.modules", {"gtts": mock_gtts_module}):
            backend = GTTSBackend()
            with pytest.raises(RuntimeError, match="network error"):
                await backend.synthesize("fail")

    def test_mp3_to_wav_returns_mp3_when_ffmpeg_missing(self):
        mp3_data = b"\xff\xfb\x90\x00"
        with (
            patch(
                "app.services.tts_gtts.subprocess.run",
                side_effect=FileNotFoundError,
            ),
            patch("app.services.tts_gtts.Path.unlink"),
        ):
            result = GTTSBackend._mp3_to_wav(mp3_data)
        assert result == mp3_data

    def test_mp3_to_wav_converts_with_ffmpeg(self):
        mp3_data = b"\xff\xfb\x90\x00"
        wav_data = b"RIFF-converted"

        with (
            patch("app.services.tts_gtts.subprocess.run") as mock_run,
            patch("app.services.tts_gtts.Path.read_bytes", return_value=wav_data),
            patch("app.services.tts_gtts.Path.unlink"),
        ):
            mock_run.return_value = MagicMock(returncode=0)
            result = GTTSBackend._mp3_to_wav(mp3_data)

        assert result == wav_data
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"


# ---------------------------------------------------------------------------
# Config integration
# ---------------------------------------------------------------------------


class TestTTSConfig:
    """TTS settings integrate with the application config."""

    def test_default_settings_have_tts_fields(self):
        from app.config import Settings

        s = Settings(
            database_encryption_key="test-key",
            _env_file=None,
        )
        assert s.tts_engine == "nanotts"
        assert s.tts_speed == 1.0
        assert s.tts_volume == 0.8

    def test_settings_accept_gtts_engine(self):
        from app.config import Settings

        s = Settings(
            tts_engine="gtts",
            database_encryption_key="test-key",
            _env_file=None,
        )
        assert s.tts_engine == "gtts"

    def test_settings_accept_custom_speed_and_volume(self):
        from app.config import Settings

        s = Settings(
            tts_speed=1.5,
            tts_volume=0.3,
            database_encryption_key="test-key",
            _env_file=None,
        )
        assert s.tts_speed == 1.5
        assert s.tts_volume == 0.3
