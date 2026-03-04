"""Tests for Mopidy music service and music intent handler."""

from __future__ import annotations

import json

import httpx
import pytest

from app.schemas.intent import Intent, IntentCategory, IntentSlot
from app.services.intent_dispatch import IntentDispatch, setup_handlers
from app.services.intent_handlers.music_handler import MusicIntentHandler
from app.services.music import MopidyMusicService


def _make_mock_service(result_by_method: dict[str, object], called: list[str]):
    def _handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8"))
        method = payload["method"]
        called.append(method)
        return httpx.Response(
            status_code=200,
            json={
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": result_by_method.get(method),
            },
        )

    transport = httpx.MockTransport(_handler)

    return MopidyMusicService(
        mopidy_url="http://test/mopidy/rpc",
        client_factory=lambda: httpx.AsyncClient(transport=transport),
    )


@pytest.mark.asyncio
async def test_music_playback_controls_issue_expected_rpc_calls():
    called: list[str] = []
    service = _make_mock_service(
        {
            "core.playback.play": True,
            "core.playback.pause": True,
            "core.playback.stop": True,
            "core.playback.next": True,
            "core.playback.previous": True,
            "core.mixer.set_volume": True,
            "core.mixer.get_volume": 33,
            "core.tracklist.set_random": True,
            "core.tracklist.set_repeat": True,
        },
        called,
    )

    assert await service.play() is True
    assert await service.pause() is True
    assert await service.stop() is True
    assert await service.next_track() is True
    assert await service.previous_track() is True
    assert await service.set_volume(55) is True
    assert await service.get_volume() == 33
    assert await service.set_shuffle(True) is True
    assert await service.set_repeat(True) is True

    assert called == [
        "core.playback.play",
        "core.playback.pause",
        "core.playback.stop",
        "core.playback.next",
        "core.playback.previous",
        "core.mixer.set_volume",
        "core.mixer.get_volume",
        "core.tracklist.set_random",
        "core.tracklist.set_repeat",
    ]


@pytest.mark.asyncio
async def test_music_search_returns_track_list():
    called: list[str] = []
    service = _make_mock_service(
        {
            "core.library.search": [
                {
                    "tracks": [
                        {
                            "uri": "local:track:1",
                            "name": "Landslide",
                            "artists": [{"name": "Fleetwood Mac"}],
                            "album": {"name": "Fleetwood Mac"},
                            "length": 193000,
                        }
                    ]
                }
            ]
        },
        called,
    )

    results = await service.search("landslide")

    assert len(results) == 1
    assert results[0].title == "Landslide"
    assert results[0].artist == "Fleetwood Mac"
    assert results[0].uri == "local:track:1"
    assert called == ["core.library.search"]


@pytest.mark.asyncio
async def test_music_service_graceful_offline_behavior():
    def _raise_unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("mopidy offline", request=request)

    service = MopidyMusicService(
        mopidy_url="http://test/mopidy/rpc",
        client_factory=lambda: httpx.AsyncClient(
            transport=httpx.MockTransport(_raise_unreachable),
        ),
    )

    state = await service.get_playback_state()

    assert state.state == "stopped"
    assert state.current_track is None
    assert state.position_ms == 0
    assert state.volume == 0
    assert state.shuffle is False
    assert state.repeat is False
    assert await service.search("anything") == []
    assert await service.play() is False


class _FakeMusicService:
    def __init__(self):
        self.calls: list[tuple[str, object | None]] = []
        self.volume = 40

    async def play(self) -> bool:
        self.calls.append(("play", None))
        return True

    async def pause(self) -> bool:
        self.calls.append(("pause", None))
        return True

    async def next_track(self) -> bool:
        self.calls.append(("next", None))
        return True

    async def previous_track(self) -> bool:
        self.calls.append(("previous", None))
        return True

    async def get_volume(self) -> int:
        self.calls.append(("get_volume", None))
        return self.volume

    async def set_volume(self, level: int) -> bool:
        self.calls.append(("set_volume", level))
        self.volume = level
        return True

    async def set_shuffle(self, enabled: bool) -> bool:
        self.calls.append(("set_shuffle", enabled))
        return True


@pytest.mark.asyncio
async def test_music_intent_handler_routes_controls_and_volume():
    music_service = _FakeMusicService()
    handler = MusicIntentHandler(music_service=music_service)

    response_play = await handler.handle(Intent(name="play_music"))
    response_pause = await handler.handle(Intent(name="pause_music"))
    response_skip = await handler.handle(Intent(name="next_song"))
    response_volume_set = await handler.handle(
        Intent(
            name="set_volume",
            slots=[IntentSlot(name="level", value="65")],
        )
    )
    response_volume_up = await handler.handle(
        Intent(name="set_volume", raw_text="volume up")
    )
    response_shuffle = await handler.handle(Intent(name="set_shuffle"))

    assert "playing" in response_play.lower()
    assert "paused" in response_pause.lower()
    assert "next" in response_skip.lower()
    assert "65" in response_volume_set
    assert "volume up" in response_volume_up.lower()
    assert "shuffle" in response_shuffle.lower()

    assert ("play", None) in music_service.calls
    assert ("pause", None) in music_service.calls
    assert ("next", None) in music_service.calls
    assert ("set_volume", 65) in music_service.calls
    assert ("set_shuffle", True) in music_service.calls


@pytest.mark.asyncio
async def test_setup_handlers_registers_music_handler_for_dispatch():
    dispatch = IntentDispatch()
    music_service = _FakeMusicService()
    setup_handlers(dispatch, music_service=music_service)

    result = await dispatch.dispatch(Intent(name="play_music"))

    assert result == "Playing music."
    assert ("play", None) in music_service.calls
    assert IntentCategory.MUSIC in dispatch._handlers
