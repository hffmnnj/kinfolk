# Architecture

Kinfolk is a single-device application: a Flutter Desktop frontend communicates with a local Python FastAPI backend over HTTP and WebSocket. Everything runs on the same machine (Raspberry Pi 5 or mini PC).

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Flutter Desktop App                           │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Dashboard   │  │ Calendar    │  │ Settings / Profiles      │ │
│  │ (clock,     │  │ (events,    │  │                          │ │
│  │  weather,   │  │  tasks)     │  │                          │ │
│  │  tasks)     │  │             │  │                          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                  │
│  State: Riverpod providers  ·  Transport: http + web_socket_channel │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP REST + WebSocket
                               │ localhost:8080
┌──────────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend                                │
│                                                                  │
│  Routers: /api/v1/{users,auth,calendar,tasks,voice,             │
│            smarthome,weather,music,timers}                       │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Services                               │   │
│  │                                                           │   │
│  │  VoicePipeline ──► WakeWordService (openWakeWord)        │   │
│  │       │        ──► STTService (Vosk / Whisper)           │   │
│  │       │        ──► NLUService (Rhasspy sentences.ini)    │   │
│  │       │        ──► IntentDispatch ──► handlers           │   │
│  │       └──────────► TTSService (NanoTTS / gTTS)           │   │
│  │                                                           │   │
│  │  CalendarSyncService ──► GoogleCalendarService           │   │
│  │                      ──► CalDAVCalendarService           │   │
│  │                                                           │   │
│  │  HomeAssistantService (REST)                             │   │
│  │  HomeAssistantWSService (WebSocket, real-time states)    │   │
│  │                                                           │   │
│  │  MopidyMusicService (JSON-RPC → Mopidy port 6680)        │   │
│  │  WeatherService (OpenWeatherMap REST)                    │   │
│  │  TimerService (DB-backed, TTS alerts on expiry)          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  SQLCipher (encrypted SQLite)                                    │
│  Tables: users · events · tasks · voice_history · timers        │
└─────────────────────────────────────────────────────────────────┘

External (optional, all opt-in):
  OpenWeatherMap API  ·  Google Calendar OAuth  ·  CalDAV servers
  Home Assistant (local network)  ·  Mopidy (local)
  OpenAI Whisper API (if STT_MODE=openai)
```

---

## Flutter Frontend — Clean Architecture

The Flutter app follows Clean Architecture with four layers. Dependencies point inward only: Infrastructure → Application → Domain. Presentation depends on Application.

```
frontend/lib/
├── main.dart                    # Entry point: ProviderScope + MaterialApp
│
├── presentation/                # UI Layer — screens, widgets, themes
│   ├── screens/                 # Full-screen views (DashboardScreen, etc.)
│   ├── widgets/                 # Reusable UI components (ClockWidget, etc.)
│   └── themes/
│       ├── kinfolk_theme.dart   # Light + dark MaterialTheme
│       ├── kinfolk_colors.dart  # Color tokens (warmClay, deepCharcoal, etc.)
│       └── kinfolk_typography.dart  # Inter font scale
│
├── application/                 # Business Logic Layer
│   ├── providers/               # Riverpod providers (state management)
│   ├── services/                # Application services (orchestration)
│   └── use_cases/               # Single-responsibility use cases
│
├── domain/                      # Core Domain Layer (no Flutter imports)
│   ├── entities/                # Business entities (User, Event, Task)
│   ├── repositories/            # Abstract repository interfaces
│   └── value_objects/           # Domain primitives
│
└── infrastructure/              # External Concerns Layer
    ├── api/                     # HTTP clients for backend API
    ├── database/                # Local SQLite (sqflite)
    └── external/                # Third-party integrations
```

### Design System

| Token | Value | Usage |
|-------|-------|-------|
| `warmClay` | `#D4A574` | Primary accent, buttons |
| `deepCharcoal` | `#2A2A2E` | Dark background |
| `softCream` | `#F5F3ED` | Light background, dark-mode text |
| `forestGreen` | `#4A7C59` | Success, secondary actions |
| `skyBlue` | `#7BA7BC` | Info, tertiary |
| `sunsetOrange` | `#E07856` | Warning, error |
| `sageGray` | `#9CA3A8` | Muted text, dividers |

Typography uses **Inter** (bundled as TTF assets — no Google Fonts CDN calls).

### State Management

Riverpod is the only state management solution. No `setState()` in the codebase.

```dart
// Example provider pattern
final weatherProvider = FutureProvider<WeatherData>((ref) async {
  final api = ref.read(apiServiceProvider);
  return api.getWeather();
});
```

---

## Backend — FastAPI Service Architecture

### Startup Sequence

On startup (`lifespan` in `main.py`), the backend:

1. Creates database tables (SQLCipher-encrypted SQLite)
2. Initializes all services (voice pipeline, calendar sync, HA WebSocket, timers)
3. Starts background tasks: wake word listener, calendar sync loop, timer checker, HA WebSocket connection
4. Registers API routers

On shutdown, all background tasks are gracefully stopped.

### Service Dependency Graph

```
VoicePipeline
  ├── WakeWordService      (openWakeWord, runs in background thread)
  ├── STTService           (delegates to VoskSTT or WhisperSTT)
  ├── NLUService           (Rhasspy sentences.ini pattern matching)
  ├── IntentDispatch       (routes intents to handlers)
  │     ├── CalendarHandler  → CalendarSyncService
  │     ├── WeatherHandler   → WeatherService
  │     ├── MusicHandler     → MopidyMusicService
  │     ├── SmartHomeHandler → HomeAssistantService
  │     └── TimerHandler     → TimerService
  └── TTSService           (delegates to NanoTTS or gTTS)

CalendarSyncService
  ├── GoogleCalendarService  (OAuth 2.0, polls every 5 min)
  └── CalDAVCalendarService  (CalDAV protocol, polls every 5 min)

HomeAssistantWSService     (persistent WebSocket, real-time state updates)
HomeAssistantService       (REST API for commands)

MopidyMusicService         (JSON-RPC to Mopidy on port 6680)
WeatherService             (OpenWeatherMap REST API)
TimerService               (DB-backed, fires TTS on expiry)
```

---

## Voice Command Pipeline

The complete flow from wake word to spoken response:

```
Microphone (sounddevice, 16kHz mono)
    │
    ▼
WakeWordService (openWakeWord)
    │  Listens continuously in background thread
    │  Detects "Hey Kin" / "Kinfolk" wake word
    │  Sensitivity: configurable (default 0.5)
    │
    ▼  [wake word detected]
STTService
    │  Records audio (3–10 seconds, VAD-based endpoint)
    │  STT_MODE=local  → VoskSTT (offline, ~vosk-model-en-us)
    │  STT_MODE=openai → WhisperSTT (OpenAI API, better accuracy)
    │  Returns: transcribed text string
    │
    ▼
NLUService (Rhasspy sentences.ini)
    │  Pattern-matches transcribed text against intent definitions
    │  File: backend/rhasspy/sentences.ini
    │  Returns: Intent name + extracted slots
    │  Example: "add milk to shopping list"
    │           → Intent: AddTask, slots: {item: "milk", list: "shopping"}
    │
    ▼
IntentDispatch
    │  Routes intent to registered handler
    │  Handlers registered in setup_handlers() at startup
    │  Returns: response text string
    │
    ▼
TTSService
    │  TTS_ENGINE=nanotts → NanoTTS (offline, requires nanotts package)
    │  TTS_ENGINE=gtts    → gTTS (Google TTS, requires internet)
    │  Speaks response through default audio output
    │
    ▼
Audio output (speaker)
```

### Adding Voice Commands

Voice commands are defined in `backend/rhasspy/sentences.ini` using Rhasspy's intent syntax:

```ini
[GetWeather]
what's the weather [today | tomorrow | this week]
will it rain [today | tomorrow]

[AddTask]
add {item} to [the] {list_name} [list]
put {item} on {list_name}

[PlayMusic]
play [some] {genre} music
play {song} by {artist}
```

Add a new intent, then register a handler in `backend/app/services/intent_handlers/`.

---

## Database Schema

The database is SQLite encrypted with SQLCipher. Tables are auto-created on startup.

### users

```sql
CREATE TABLE users (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    email       TEXT,
    role        TEXT NOT NULL,      -- admin | adult | child | guest
    preferences JSON,               -- per-user settings blob
    created_at  TIMESTAMP,
    last_active TIMESTAMP
);
```

### events

```sql
CREATE TABLE events (
    id          TEXT PRIMARY KEY,
    user_id     TEXT REFERENCES users(id),
    title       TEXT NOT NULL,
    start_time  TIMESTAMP NOT NULL,
    end_time    TIMESTAMP NOT NULL,
    location    TEXT,
    attendees   JSON,               -- list of attendee strings
    source      TEXT,               -- local | google | caldav
    external_id TEXT                -- ID in the external calendar system
);
```

### tasks

```sql
CREATE TABLE tasks (
    id          TEXT PRIMARY KEY,
    user_id     TEXT REFERENCES users(id),
    title       TEXT NOT NULL,
    description TEXT,
    due_date    TIMESTAMP,
    priority    TEXT,               -- low | medium | high
    completed   BOOLEAN DEFAULT FALSE,
    list_id     TEXT,               -- shopping | chores | custom
    created_at  TIMESTAMP
);
```

### voice_history

```sql
CREATE TABLE voice_history (
    id        TEXT PRIMARY KEY,
    user_id   TEXT REFERENCES users(id),
    command   TEXT,                 -- transcribed text
    intent    TEXT,                 -- matched intent name
    response  TEXT,                 -- TTS response text
    timestamp TIMESTAMP
);
```

### timers

```sql
CREATE TABLE timers (
    id         TEXT PRIMARY KEY,
    user_id    TEXT REFERENCES users(id),
    label      TEXT,                -- "cookies", "laundry", etc.
    duration   INTEGER,             -- seconds
    expires_at TIMESTAMP,
    fired      BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP
);
```

---

## API Endpoint Reference

**Base URL:** `http://localhost:8080/api/v1`

**Interactive docs:** `http://localhost:8080/docs` (Swagger UI)

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check → `{"status":"healthy"}` |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| GET | `/auth/google` | Initiate Google OAuth flow |
| GET | `/auth/google/callback` | OAuth callback (redirect URI) |

### Users

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | List all users |
| POST | `/users` | Create user |
| GET | `/users/{id}` | Get user by ID |
| PUT | `/users/{id}` | Update user |
| DELETE | `/users/{id}` | Delete user |

### Calendar

| Method | Path | Description |
|--------|------|-------------|
| GET | `/calendar/events` | List events (supports `?start=&end=` filters) |
| POST | `/calendar/events` | Create event |
| PUT | `/calendar/events/{id}` | Update event |
| DELETE | `/calendar/events/{id}` | Delete event |
| POST | `/calendar/sync` | Trigger manual sync with Google/CalDAV |

### Tasks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/tasks` | List tasks (supports `?list_id=&user_id=` filters) |
| POST | `/tasks` | Create task |
| PUT | `/tasks/{id}` | Update task (including marking complete) |
| DELETE | `/tasks/{id}` | Delete task |

### Voice

| Method | Path | Description |
|--------|------|-------------|
| POST | `/voice/command` | Submit a text command (bypasses STT) |
| GET | `/voice/history` | Recent voice command history |
| POST | `/voice/tts` | Convert text to speech (returns audio) |
| GET | `/voice/ws` | WebSocket — real-time voice pipeline events |

### Smart Home

| Method | Path | Description |
|--------|------|-------------|
| GET | `/smarthome/devices` | List HA entities |
| POST | `/smarthome/devices/{entity_id}/command` | Send command to entity |
| GET | `/smarthome/scenes` | List HA scenes |
| POST | `/smarthome/scenes/{scene_id}/activate` | Activate scene |
| GET | `/smarthome/ws` | WebSocket — real-time HA state updates |

### Weather

| Method | Path | Description |
|--------|------|-------------|
| GET | `/weather/current` | Current conditions |
| GET | `/weather/forecast` | 5-day forecast |

### Music

| Method | Path | Description |
|--------|------|-------------|
| GET | `/music/status` | Current playback state |
| POST | `/music/play` | Play (optionally with `uri` body) |
| POST | `/music/pause` | Pause playback |
| POST | `/music/next` | Skip to next track |
| POST | `/music/previous` | Previous track |
| GET | `/music/search` | Search library (`?q=query`) |
| GET | `/music/queue` | Current play queue |

### Timers

| Method | Path | Description |
|--------|------|-------------|
| GET | `/timers` | List active timers |
| POST | `/timers` | Create timer (`{label, duration_seconds}`) |
| DELETE | `/timers/{id}` | Cancel timer |

### Response Format

All endpoints return a consistent envelope:

```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "2026-03-04T12:00:00Z"
}
```

Errors:

```json
{
  "status": "error",
  "error": {
    "code": "NOT_FOUND",
    "message": "User not found"
  },
  "timestamp": "2026-03-04T12:00:00Z"
}
```

---

## Communication Patterns

### Flutter → Backend (REST)

Standard HTTP requests using the `http` package. The Flutter app talks to `http://localhost:8080/api/v1`.

### Flutter → Backend (WebSocket)

Real-time updates (HA state changes, voice pipeline events) use WebSocket via `web_socket_channel`. The backend pushes events; the Flutter app subscribes.

### Backend → Home Assistant

Two channels run in parallel:
- **REST** (`HomeAssistantService`): Commands (turn on light, activate scene)
- **WebSocket** (`HomeAssistantWSService`): Persistent connection for real-time state updates. Reconnects automatically on disconnect.

### Backend → Mopidy

JSON-RPC over HTTP to Mopidy's built-in HTTP server (port 6680). No persistent connection needed.

### Backend → Calendar Sources

Background polling loop (every 5 minutes) pulls events from Google Calendar and CalDAV servers, merges them into the local SQLite database, and resolves conflicts (server wins).

---

## Security Model

- **Database at rest:** SQLCipher AES-256 encryption. Key set via `DATABASE_ENCRYPTION_KEY`.
- **No cloud by default:** All processing is local. Cloud services (Google Calendar, OpenAI Whisper) are opt-in.
- **CORS:** Configured to allow only the Flutter app origin. Never uses wildcard + credentials.
- **HA token:** Stored in `.env`, never logged or exposed via API.
- **Voice audio:** Not stored by default. `voice_history` table stores transcribed text only.
