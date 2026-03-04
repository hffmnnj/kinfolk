"""Tests for Google Calendar OAuth and adapter behavior."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from app.domain.calendar_event import CalendarEvent
from app.services.calendar_google import GoogleCalendarService


class _FakeCredentials:
    def __init__(
        self,
        *,
        expired: bool = False,
        refresh_token: str | None = "refresh-token",
        access_token: str = "access-token",
    ) -> None:
        self.expired = expired
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.refresh_calls = 0

    def refresh(self, request: Any) -> None:
        del request
        self.refresh_calls += 1
        self.expired = False
        self.access_token = "refreshed-token"

    def to_json(self) -> str:
        payload = {
            "token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "test-client-id",
            "client_secret": "test-client-secret",
            "scopes": ["https://www.googleapis.com/auth/calendar"],
        }
        return json.dumps(payload)


class _Executable:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def execute(self) -> dict[str, Any]:
        return self._payload


class _FakeEventsResource:
    def __init__(self) -> None:
        self.list_kwargs: dict[str, Any] | None = None
        self.insert_kwargs: dict[str, Any] | None = None

    def list(self, **kwargs: Any) -> _Executable:
        self.list_kwargs = kwargs
        return _Executable(
            {
                "items": [
                    {
                        "id": "google-event-1",
                        "summary": "Team standup",
                        "start": {"dateTime": "2026-03-04T09:00:00Z"},
                        "end": {"dateTime": "2026-03-04T09:30:00Z"},
                        "location": "Kitchen",
                        "description": "Daily sync",
                        "attendees": [{"email": "a@example.com"}],
                    }
                ]
            }
        )

    def insert(self, **kwargs: Any) -> _Executable:
        self.insert_kwargs = kwargs
        body = kwargs["body"]
        return _Executable(
            {
                "id": "google-event-created",
                "summary": body.get("summary"),
                "start": body.get("start"),
                "end": body.get("end"),
                "location": body.get("location"),
                "description": body.get("description"),
                "attendees": body.get("attendees", []),
            }
        )

    def delete(self, **kwargs: Any) -> _Executable:
        return _Executable(kwargs)


class _FakeCalendarServiceClient:
    def __init__(self) -> None:
        self.events_resource = _FakeEventsResource()

    def events(self) -> _FakeEventsResource:
        return self.events_resource


class _FakeFlow:
    def __init__(self) -> None:
        self.fetch_code: str | None = None
        self.credentials = _FakeCredentials()

    def authorization_url(self, **kwargs: Any) -> tuple[str, str]:
        assert kwargs["access_type"] == "offline"
        assert kwargs["include_granted_scopes"] == "true"
        return "https://accounts.google.com/o/oauth2/auth?state=test", "test"

    def fetch_token(self, code: str) -> None:
        self.fetch_code = code


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        google_client_id="test-client-id",
        google_client_secret="test-client-secret",
        google_redirect_uri="http://localhost:8080/api/v1/auth/google/callback",
    )


def _build_service(
    tmp_path: Path,
    credentials: _FakeCredentials,
    fake_client: _FakeCalendarServiceClient,
) -> GoogleCalendarService:
    token_path = tmp_path / "google_token.json"
    token_path.write_text(json.dumps({"token": "seed"}), encoding="utf-8")

    return GoogleCalendarService(
        settings=_settings(),
        token_path=token_path,
        flow_factory=lambda **kwargs: _FakeFlow(),
        credentials_loader=lambda token_data, scopes: credentials,
        build_service=lambda creds: fake_client,
        refresh_request_factory=lambda: object(),
    )


def test_get_auth_url_generation(tmp_path: Path) -> None:
    """OAuth start endpoint should generate a consent URL."""
    flow = _FakeFlow()
    service = GoogleCalendarService(
        settings=_settings(),
        token_path=tmp_path / "google_token.json",
        flow_factory=lambda **kwargs: flow,
    )

    auth_url = service.get_auth_url()

    assert auth_url.startswith("https://accounts.google.com/o/oauth2/auth")


def test_list_events_maps_google_response(tmp_path: Path) -> None:
    """Google list response maps into domain CalendarEvent entities."""
    credentials = _FakeCredentials()
    client = _FakeCalendarServiceClient()
    service = _build_service(tmp_path, credentials, client)

    events = service.list_events(
        start=datetime(2026, 3, 4, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 5, 0, 0, tzinfo=timezone.utc),
    )

    assert len(events) == 1
    assert events[0].title == "Team standup"
    assert events[0].source == "google"
    assert events[0].external_id == "google-event-1"
    assert client.events_resource.list_kwargs is not None
    assert client.events_resource.list_kwargs["calendarId"] == "primary"


def test_create_event_sends_payload_and_maps_response(tmp_path: Path) -> None:
    """Creating an event sends a Google payload and maps response values."""
    credentials = _FakeCredentials()
    client = _FakeCalendarServiceClient()
    service = _build_service(tmp_path, credentials, client)

    created = service.create_event(
        CalendarEvent(
            title="Doctor",
            start_time=datetime(2026, 3, 6, 14, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 3, 6, 14, 30, tzinfo=timezone.utc),
            location="Clinic",
            description="Annual checkup",
            attendees=["family@example.com"],
            source="local",
        )
    )

    assert created.external_id == "google-event-created"
    assert created.title == "Doctor"
    assert created.source == "google"
    assert client.events_resource.insert_kwargs is not None
    assert client.events_resource.insert_kwargs["calendarId"] == "primary"
    assert (
        client.events_resource.insert_kwargs["body"]["attendees"][0]["email"]
        == "family@example.com"
    )


def test_token_refresh_happens_and_is_persisted(tmp_path: Path) -> None:
    """Expired credentials should auto-refresh and persist the new token."""
    credentials = _FakeCredentials(expired=True)
    client = _FakeCalendarServiceClient()
    service = _build_service(tmp_path, credentials, client)

    _ = service.list_events(
        start=datetime(2026, 3, 4, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 5, 0, 0, tzinfo=timezone.utc),
    )

    token_path = tmp_path / "google_token.json"
    saved = json.loads(token_path.read_text(encoding="utf-8"))
    assert credentials.refresh_calls == 1
    assert saved["token"] == "refreshed-token"


def test_graceful_when_google_credentials_not_configured(caplog) -> None:
    """Missing OAuth configuration should degrade gracefully for listing."""
    service = GoogleCalendarService(
        settings=SimpleNamespace(
            google_client_id=None,
            google_client_secret=None,
            google_redirect_uri="",
        )
    )

    events = service.list_events(
        start=datetime(2026, 3, 4, 0, 0, tzinfo=timezone.utc),
        end=datetime(2026, 3, 5, 0, 0, tzinfo=timezone.utc),
    )

    assert events == []
    assert "not configured" in caplog.text.lower()
