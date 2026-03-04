"""Schemas for music playback and library data."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Track(BaseModel):
    """Normalized track payload from Mopidy."""

    id: str
    title: str
    artist: str
    album: str
    duration_ms: int
    uri: str


class Playlist(BaseModel):
    """Library node for folders/playlists in browse responses."""

    id: str
    name: str
    uri: str


class PlaybackState(BaseModel):
    """Current player state used by status APIs and voice responses."""

    state: Literal["playing", "paused", "stopped"] = "stopped"
    current_track: Track | None = None
    position_ms: int = 0
    volume: int = 0
    shuffle: bool = False
    repeat: bool = False
