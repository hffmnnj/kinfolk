"""Google Calendar source adapter with OAuth token persistence."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from app.config import settings as app_settings
from app.domain.calendar_event import CalendarEvent

LOGGER = logging.getLogger(__name__)

GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarSource(Protocol):
    """Contract for calendar source integrations."""

    def list_events(
        self,
        start: datetime,
        end: datetime,
    ) -> list[CalendarEvent]:
        """Return events in the requested date range."""
        ...

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        """Create an event in the external calendar source."""
        ...

    def delete_event(self, event_id: str) -> None:
        """Delete an event by provider-specific id."""
        ...


class GoogleCalendarConfigError(RuntimeError):
    """Raised when Google OAuth is not configured."""


class GoogleCalendarAuthError(RuntimeError):
    """Raised when Google OAuth credentials are unavailable."""


class GoogleCalendarService(CalendarSource):
    """Google Calendar integration with OAuth token lifecycle management."""

    def __init__(
        self,
        settings: Any = app_settings,
        token_path: Path | None = None,
        flow_factory: Callable[..., Any] | None = None,
        credentials_loader: Callable[..., Any] | None = None,
        build_service: Callable[..., Any] | None = None,
        refresh_request_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._client_id = getattr(settings, "google_client_id", None)
        self._client_secret = getattr(settings, "google_client_secret", None)
        self._redirect_uri = getattr(settings, "google_redirect_uri", "")
        default_token = (
            Path(__file__).resolve().parents[3] / ".kinfolk" / "google_token.json"  # noqa: E501
        )
        self._token_path = token_path or default_token
        self._flow_factory = flow_factory or self._default_flow_factory
        self._credentials_loader = (
            credentials_loader or self._default_credentials_loader
        )
        self._build_service = build_service or self._default_build_service
        self._refresh_request_factory = (
            refresh_request_factory or self._default_refresh_request_factory
        )

    def get_auth_url(self) -> str:
        """Create Google OAuth consent URL for first-time authentication."""
        self._require_configured()
        flow = self._build_oauth_flow()
        auth_url, _state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    def handle_callback(self, code: str, state: str | None = None) -> None:
        """Exchange callback code for tokens and persist to disk."""
        if not code.strip():
            raise GoogleCalendarAuthError("Missing OAuth callback code.")

        self._require_configured()
        flow = self._build_oauth_flow(state=state)
        flow.fetch_token(code=code)
        self._save_credentials(flow.credentials)

    def list_events(
        self,
        start: datetime,
        end: datetime,
    ) -> list[CalendarEvent]:
        """Fetch events from Google Calendar in a date range."""
        if not self._is_configured():
            LOGGER.warning(
                "Google Calendar credentials are not configured; returning no events."  # noqa: E501
            )
            return []

        credentials = self._load_credentials()
        if credentials is None:
            LOGGER.warning(
                "Google Calendar token is unavailable; returning no events. "
                "Run OAuth authorization first."
            )
            return []

        service = self._build_service(credentials)
        response = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=self._to_google_datetime(start),
                timeMax=self._to_google_datetime(end),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = response.get("items", [])
        return [self._google_to_calendar_event(item) for item in items]

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        """Create an event in Google Calendar."""
        if not self._is_configured():
            LOGGER.warning(
                "Google Calendar credentials are not configured; "
                "skipping remote event creation."
            )
            return event.model_copy(update={"source": "google"})

        credentials = self._load_credentials()
        if credentials is None:
            LOGGER.warning(
                "Google Calendar token is unavailable; skipping remote event creation."  # noqa: E501
            )
            return event.model_copy(update={"source": "google"})

        service = self._build_service(credentials)
        payload = {
            "summary": event.title,
            "location": event.location,
            "description": event.description,
            "start": {"dateTime": self._to_google_datetime(event.start_time)},
            "end": {"dateTime": self._to_google_datetime(event.end_time)},
            "attendees": [{"email": email} for email in event.attendees],
        }
        response = service.events().insert(calendarId="primary", body=payload).execute()  # noqa: E501
        return self._google_to_calendar_event(response)

    def delete_event(self, event_id: str) -> None:
        """Delete a Google Calendar event by id."""
        if not event_id:
            return

        if not self._is_configured():
            LOGGER.warning(
                "Google Calendar credentials are not configured; "
                "skipping remote event delete."
            )
            return

        credentials = self._load_credentials()
        if credentials is None:
            LOGGER.warning(
                "Google Calendar token is unavailable; skipping remote event delete."  # noqa: E501
            )
            return

        service = self._build_service(credentials)
        (service.events().delete(calendarId="primary", eventId=event_id).execute())  # noqa: E501

    def _build_oauth_flow(self, state: str | None = None) -> Any:
        assert isinstance(self._client_id, str)
        assert isinstance(self._client_secret, str)
        return self._flow_factory(
            client_id=self._client_id,
            client_secret=self._client_secret,
            redirect_uri=self._redirect_uri,
            scopes=GOOGLE_CALENDAR_SCOPES,
            state=state,
        )

    def _load_credentials(self) -> Any | None:
        token_data = self._read_token_data()
        if token_data is None:
            return None

        credentials = self._credentials_loader(
            token_data,
            GOOGLE_CALENDAR_SCOPES,
        )
        if credentials is None:
            return None

        if getattr(credentials, "expired", False):
            refresh_token = getattr(credentials, "refresh_token", None)
            if not refresh_token:
                LOGGER.warning(
                    "Google token is expired and has no refresh token; "
                    "re-authentication required."
                )
                return None

            credentials.refresh(self._refresh_request_factory())
            self._save_credentials(credentials)

        return credentials

    def _read_token_data(self) -> dict[str, Any] | None:
        if not self._token_path.exists():
            return None

        try:
            raw = self._token_path.read_text(encoding="utf-8")
            return json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Failed to read Google token file: %s", exc)
            return None

    def _save_credentials(self, credentials: Any) -> None:
        token_json = credentials.to_json()
        token_data = json.loads(token_json)

        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(
            json.dumps(token_data, indent=2),
            encoding="utf-8",
        )

    def _require_configured(self) -> None:
        if not self._is_configured():
            raise GoogleCalendarConfigError(
                "Google OAuth is not configured. Set GOOGLE_CLIENT_ID, "
                "GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI."
            )

    def _is_configured(self) -> bool:
        return bool(
            self._client_id
            and str(self._client_id).strip()
            and self._client_secret
            and str(self._client_secret).strip()
            and self._redirect_uri
            and str(self._redirect_uri).strip()
        )

    def _google_to_calendar_event(self, item: dict[str, Any]) -> CalendarEvent:
        start_payload = item.get("start", {})
        end_payload = item.get("end", {})
        start_raw = start_payload.get("dateTime") or start_payload.get("date")
        end_raw = end_payload.get("dateTime") or end_payload.get("date")

        attendees = item.get("attendees") or []
        attendee_emails = [
            email
            for attendee in attendees
            for email in [attendee.get("email")]
            if isinstance(attendee, dict) and isinstance(email, str)
        ]

        google_id = item.get("id")
        return CalendarEvent(
            id=google_id,
            title=item.get("summary", "Untitled"),
            start_time=self._parse_google_datetime(start_raw),
            end_time=self._parse_google_datetime(end_raw),
            location=item.get("location"),
            description=item.get("description"),
            attendees=attendee_emails,
            source="google",
            external_id=google_id,
        )

    @staticmethod
    def _parse_google_datetime(raw_value: Any) -> datetime:
        if not isinstance(raw_value, str) or not raw_value.strip():
            return datetime.now(timezone.utc)

        value = raw_value.strip()
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))

        parsed_date = date.fromisoformat(value)
        return datetime.combine(parsed_date, time.min, tzinfo=timezone.utc)

    @staticmethod
    def _to_google_datetime(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _default_flow_factory(
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: list[str],
        state: str | None,
    ) -> Any:
        from google_auth_oauthlib.flow import Flow

        client_config = {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=scopes,
            state=state,
        )
        flow.redirect_uri = redirect_uri
        return flow

    @staticmethod
    def _default_credentials_loader(
        token_data: dict[str, Any],
        scopes: list[str],
    ) -> Any:
        from google.oauth2.credentials import Credentials

        return Credentials.from_authorized_user_info(token_data, scopes)

    @staticmethod
    def _default_build_service(credentials: Any) -> Any:
        from googleapiclient.discovery import build

        return build(
            "calendar",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    @staticmethod
    def _default_refresh_request_factory() -> Any:
        from google.auth.transport.requests import Request

        return Request()
