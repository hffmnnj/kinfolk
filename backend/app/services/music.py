"""Mopidy JSON-RPC music service."""

from __future__ import annotations

import logging
from typing import Any, Callable, Literal, cast

import httpx

from app.config import settings
from app.schemas.music import PlaybackState, Playlist, Track

LOGGER = logging.getLogger(__name__)


class MopidyMusicService:
    """Async Mopidy client for playback, browse, and search operations."""

    def __init__(
        self,
        mopidy_url: str | None = None,
        timeout_seconds: float = 5.0,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self._mopidy_url = mopidy_url or settings.mopidy_url
        self._timeout_seconds = timeout_seconds
        self._client_factory = client_factory or self._default_client_factory
        self._request_id = 0

    async def play(self) -> bool:
        return await self._bool_call("core.playback.play")

    async def pause(self) -> bool:
        return await self._bool_call("core.playback.pause")

    async def stop(self) -> bool:
        return await self._bool_call("core.playback.stop")

    async def next_track(self) -> bool:
        return await self._bool_call("core.playback.next")

    async def previous_track(self) -> bool:
        return await self._bool_call("core.playback.previous")

    async def set_volume(self, level: int) -> bool:
        clamped = max(0, min(100, int(level)))
        result = await self._rpc_call(
            "core.mixer.set_volume",
            {"volume": clamped},
        )
        return result is not None

    async def get_volume(self) -> int:
        result = await self._rpc_call("core.mixer.get_volume")
        if result is None:
            return 0
        try:
            return int(result)
        except (TypeError, ValueError):
            return 0

    async def set_shuffle(self, enabled: bool) -> bool:
        result = await self._rpc_call(
            "core.tracklist.set_random",
            {"value": bool(enabled)},
        )
        return result is not None

    async def set_repeat(self, enabled: bool) -> bool:
        result = await self._rpc_call(
            "core.tracklist.set_repeat",
            {"value": bool(enabled)},
        )
        return result is not None

    async def search(self, query: str) -> list[Track]:
        query = (query or "").strip()
        if not query:
            return []

        result = await self._rpc_call(
            "core.library.search",
            {
                "query": {"any": [query]},
                "uris": ["local:"],
                "exact": False,
            },
        )
        if not isinstance(result, list):
            return []

        tracks: list[Track] = []
        for search_result in result:
            for raw_track in search_result.get("tracks", []):
                track = self._track_from_mopidy(raw_track)
                if track is not None:
                    tracks.append(track)
        return tracks

    async def browse(self, path: str = "") -> list[Track | Playlist]:
        browse_uri = path.strip() or "local:directory"
        result = await self._rpc_call(
            "core.library.browse",
            {"uri": browse_uri},
        )
        if not isinstance(result, list):
            return []

        items: list[Track | Playlist] = []
        for entry in result:
            entry_type = (entry.get("type") or "").lower()
            if entry_type == "track":
                track = self._track_from_mopidy(entry)
                if track is not None:
                    items.append(track)
                continue

            items.append(
                Playlist(
                    id=str(entry.get("uri") or ""),
                    name=str(entry.get("name") or ""),
                    uri=str(entry.get("uri") or ""),
                )
            )

        return items

    async def get_playback_state(self) -> PlaybackState:
        state_value = await self._rpc_call("core.playback.get_state")
        state = str(state_value or "stopped").lower()
        if state not in {"playing", "paused", "stopped"}:
            state = "stopped"
        safe_state = cast(Literal["playing", "paused", "stopped"], state)

        tl_track = await self._rpc_call("core.playback.get_current_tl_track")
        if isinstance(tl_track, dict):
            track_payload = tl_track.get("track")
        else:
            track_payload = None
        current_track = self._track_from_mopidy(track_payload)

        position = await self._rpc_call("core.playback.get_time_position")
        shuffle = await self._rpc_call("core.tracklist.get_random")
        repeat = await self._rpc_call("core.tracklist.get_repeat")
        volume = await self.get_volume()

        return PlaybackState(
            state=safe_state,
            current_track=current_track,
            position_ms=self._as_int(position, default=0),
            volume=volume,
            shuffle=bool(shuffle),
            repeat=bool(repeat),
        )

    async def _bool_call(self, method: str) -> bool:
        result = await self._rpc_call(method)
        return result is not None

    async def _rpc_call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> Any | None:
        self._request_id += 1
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }

        try:
            async with self._client_factory() as client:
                response = await client.post(self._mopidy_url, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            LOGGER.warning(
                "Mopidy unreachable for method %s: %s",
                method,
                exc,
            )
            return None

        try:
            body = response.json()
        except ValueError:
            LOGGER.warning("Invalid JSON from Mopidy for method %s", method)
            return None

        if body.get("error"):
            LOGGER.warning(
                "Mopidy returned error for %s: %s",
                method,
                body["error"],
            )
            return None

        return body.get("result")

    def _default_client_factory(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._timeout_seconds)

    @staticmethod
    def _track_from_mopidy(raw_track: dict[str, Any] | None) -> Track | None:
        if not isinstance(raw_track, dict):
            return None

        artist_name = ""
        artists = raw_track.get("artists") or []
        if artists and isinstance(artists[0], dict):
            artist_name = str(artists[0].get("name") or "")

        album_name = ""
        album = raw_track.get("album")
        if isinstance(album, dict):
            album_name = str(album.get("name") or "")

        uri = str(raw_track.get("uri") or "")
        title = str(raw_track.get("name") or raw_track.get("title") or "")
        return Track(
            id=uri,
            title=title,
            artist=artist_name,
            album=album_name,
            duration_ms=MopidyMusicService._as_int(raw_track.get("length"), 0),
            uri=uri,
        )

    @staticmethod
    def _as_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
