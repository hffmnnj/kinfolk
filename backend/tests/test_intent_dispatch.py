"""Tests for intent dispatch registry and fallback behavior."""

from __future__ import annotations

import pytest

from app.schemas.intent import Intent, IntentCategory
from app.services.intent_dispatch import IntentDispatch


@pytest.mark.asyncio
async def test_register_handler_overrides_category_dispatch():
    dispatch = IntentDispatch()

    async def _custom_weather_handler(intent: Intent) -> str:
        del intent
        return "Custom weather response"

    dispatch.register_handler(IntentCategory.WEATHER, _custom_weather_handler)

    result = await dispatch.dispatch(Intent(name="get_weather"))

    assert result == "Custom weather response"


@pytest.mark.asyncio
async def test_dispatch_routes_intent_to_correct_stub_category():
    dispatch = IntentDispatch()

    result = await dispatch.dispatch(Intent(name="set_timer"))

    assert result == "I'll handle timers soon."


@pytest.mark.asyncio
async def test_dispatch_falls_back_for_unknown_intent():
    dispatch = IntentDispatch()

    result = await dispatch.dispatch(Intent(name="mystery_intent"))

    assert result == "I didn't understand that. Please try again."


@pytest.mark.asyncio
async def test_dispatch_returns_string_response_from_sync_handler():
    dispatch = IntentDispatch()

    def _sync_system_handler(intent: Intent) -> str:
        del intent
        return "System updated"

    dispatch.register_handler(IntentCategory.SYSTEM, _sync_system_handler)

    result = await dispatch.dispatch(Intent(name="sleep_system"))

    assert isinstance(result, str)
    assert result == "System updated"
