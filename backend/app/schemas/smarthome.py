"""Schemas for Home Assistant smart home integration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SmartDevice(BaseModel):
    """Smart home device state payload."""

    entity_id: str
    name: str
    state: str
    domain: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class DeviceCommand(BaseModel):
    """Command payload for device control endpoints."""

    command: str
    params: dict[str, Any] = Field(default_factory=dict)
