# Kinfolk - System Architecture

**Version:** 0.1.0  
**Last Updated:** March 2026

---

## Architecture Overview

Kinfolk uses a **layered architecture** with clear separation of concerns:

1. **Presentation Layer** (Flutter UI)
2. **Application Layer** (Business logic, services)
3. **Data Layer** (Storage, APIs)
4. **Infrastructure Layer** (Hardware, OS, network)

---

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACE                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Flutter Desktop Application                  │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐    │    │
│  │  │Screens   │ │Widgets   │ │State Management  │    │    │
│  │  │(Views)   │ │(UI       │ │(Riverpod)        │    │    │
│  │  │          │ │Components)│ │                  │    │    │
│  │  └──────────┘ └──────────┘ └──────────────────┘    │    │
│  └─────────────────────────────────────────────────────┘    │
│              ↕ Dart FFI / HTTP / WebSocket                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    BACKEND SERVICES                          │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────┐   │
│  │Voice Service  │  │Calendar Service│  │Media Service │   │
│  │(Python/       │  │(Python/Dart)   │  │(Mopidy)      │   │
│  │Rhasspy)       │  │                │  │              │   │
│  └───────────────┘  └────────────────┘  └──────────────┘   │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────┐   │
│  │Smart Home API │  │Photo Manager   │  │Task Manager  │   │
│  │(HA Bridge)    │  │                │  │              │   │
│  └───────────────┘  └────────────────┘  └──────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         REST API Server (Python FastAPI)             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                        DATA LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │SQLite        │  │File System   │  │Redis Cache       │  │
│  │(Main DB)     │  │(Media,Photos)│  │(Optional)        │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │Home Assistant│  │Google        │  │Spotify           │  │
│  │              │  │Calendar/Photos│  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │OpenWeatherMap│  │Whisper API   │  │News APIs         │  │
│  │              │  │(STT)         │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Flutter Application (Frontend)

**Technology:** Flutter Desktop (Dart)

**Responsibilities:**
- UI rendering (60fps)
- Touch input handling
- State management
- Local caching
- WebSocket connections
- Media playback

**Architecture Pattern:** Clean Architecture + MVVM

```
lib/
├── presentation/         # UI Layer
│   ├── screens/         # Full-screen views
│   ├── widgets/         # Reusable components
│   └── themes/          # Styling
├── application/          # Business Logic
│   ├── providers/       # State management (Riverpod)
│   ├── services/        # Business services
│   └── use_cases/       # Application use cases
├── domain/              # Core Domain
│   ├── entities/        # Business entities
│   ├── repositories/    # Repository interfaces
│   └── value_objects/   # Domain primitives
└── infrastructure/      # External Concerns
    ├── api/            # API clients
    ├── database/       # Local database
    └── external/       # Third-party integrations
```

**Key Dependencies:**
```yaml
dependencies:
  flutter:
    sdk: flutter
  riverpod: ^2.5.0              # State management
  http: ^1.2.0                  # HTTP client
  sqflite: ^2.3.0               # SQLite
  audioplayers: ^6.0.0          # Audio playback
  video_player: ^2.8.0          # Video playback
  web_socket_channel: ^3.0.0    # WebSocket
  flutter_secure_storage: ^9.0.0 # Secure storage
  google_sign_in: ^6.2.0        # OAuth
  camera: ^0.11.0               # Camera access
```

---

### 2. Backend API Server

**Technology:** FastAPI (Python)

**Responsibilities:**
- REST API endpoints
- WebSocket server
- Business logic coordination
- Authentication/authorization
- Background tasks (cron jobs)

**File Structure:**
```
backend/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── database.py          # DB connection
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API endpoints
│   │   ├── users.py
│   │   ├── calendar.py
│   │   ├── tasks.py
│   │   ├── voice.py
│   │   └── smarthome.py
│   ├── services/            # Business logic
│   │   ├── calendar_service.py
│   │   ├── voice_service.py
│   │   └── smarthome_service.py
│   └── utils/               # Helpers
├── tests/
├── requirements.txt
└── docker-compose.yml
```

**API Startup:**
```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import users, calendar, tasks

app = FastAPI(title="Kinfolk API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/api/v1/users")
app.include_router(calendar.router, prefix="/api/v1/calendar")
app.include_router(tasks.router, prefix="/api/v1/tasks")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

### 3. Voice Processing Pipeline

**Components:**
1. **Wake Word Detection** (Rhasspy/Porcupine)
2. **Audio Recording** (PyAudio)
3. **Speech-to-Text** (Whisper API or local Vosk)
4. **Intent Recognition** (Rhasspy NLU)
5. **Command Execution** (Action handlers)
6. **Text-to-Speech** (NanoTTS or gTTS)

**Flow:**
```python
# voice_service.py
class VoiceService:
    def __init__(self):
        self.wake_word_detector = PorcupineWakeWord()
        self.stt_client = WhisperSTT()
        self.intent_parser = RhasspyNLU()
        self.tts_engine = NanoTTS()
        
    async def listen(self):
        while True:
            if await self.wake_word_detector.detect():
                audio = await self.record_audio()
                text = await self.stt_client.transcribe(audio)
                intent = self.intent_parser.parse(text)
                response = await self.execute_intent(intent)
                await self.tts_engine.speak(response)
```

**Intent Configuration:**
```yaml
# intents.yaml
intents:
  AddTask:
    patterns:
      - "add {item} to [the] {list_name} [list]"
      - "put {item} on {list_name}"
    slots:
      item: text
      list_name: [shopping, chores, todo]
      
  GetWeather:
    patterns:
      - "what's the weather [today|tomorrow|this week]"
      - "will it rain [today|tomorrow]"
```

---

### 4. Calendar Service

**Technology:** Python (CalDAV) + Google Calendar API

**Data Flow:**
```
User creates event in UI
    ↓
Flutter app → POST /api/calendar/events
    ↓
Backend validates & stores in SQLite
    ↓
Background sync job → Push to CalDAV/Google
    ↓
Periodic sync (every 5min) ← Pull from CalDAV/Google
    ↓
WebSocket pushes updates to Flutter app
```

**CalDAV Integration:**
```python
# calendar_service.py
import caldav
from datetime import datetime

class CalendarService:
    def __init__(self, url, username, password):
        self.client = caldav.DAVClient(
            url=url,
            username=username,
            password=password
        )
        self.calendar = self.client.principal().calendars()[0]
        
    def get_events(self, start, end):
        events = self.calendar.date_search(start, end)
        return [self._parse_event(e) for e in events]
        
    def create_event(self, title, start, end, description=None):
        vcal = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:{start.strftime('%Y%m%dT%H%M%S')}
DTEND:{end.strftime('%Y%m%dT%H%M%S')}
SUMMARY:{title}
DESCRIPTION:{description or ''}
END:VEVENT
END:VCALENDAR"""
        self.calendar.add_event(vcal)
```

---

### 5. Smart Home Integration

**Backend:** Home Assistant

**Communication Protocol:**
- REST API for commands
- WebSocket for real-time state updates

**Connection:**
```python
# smarthome_service.py
import aiohttp

class HomeAssistantClient:
    def __init__(self, base_url, access_token):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
    async def call_service(self, domain, service, entity_id, **kwargs):
        url = f"{self.base_url}/api/services/{domain}/{service}"
        data = {"entity_id": entity_id, **kwargs}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=self.headers, json=data) as resp:
                return await resp.json()
                
    async def get_state(self, entity_id):
        url = f"{self.base_url}/api/states/{entity_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as resp:
                return await resp.json()
```

**WebSocket Subscription:**
```python
async def subscribe_to_states():
    async with websockets.connect(ws_url) as websocket:
        await websocket.send(json.dumps({
            "type": "auth",
            "access_token": token
        }))
        await websocket.send(json.dumps({
            "type": "subscribe_events",
            "event_type": "state_changed"
        }))
        while True:
            message = await websocket.recv()
            handle_state_change(json.loads(message))
```

---

### 6. Database Schema

**Technology:** SQLite + SQLAlchemy ORM

**Tables:**

**users**
```sql
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL,  -- admin, adult, child, guest
    profile_photo TEXT,
    preferences JSON,
    created_at TIMESTAMP,
    last_active TIMESTAMP
);
```

**events**
```sql
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    title TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    location TEXT,
    description TEXT,
    attendees JSON,
    recurrence TEXT,  -- RRULE
    reminders JSON,
    color TEXT,
    source TEXT,  -- local, google, caldav
    external_id TEXT
);
```

**tasks**
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    title TEXT NOT NULL,
    description TEXT,
    due_date TIMESTAMP,
    priority TEXT,  -- low, medium, high
    completed BOOLEAN DEFAULT FALSE,
    list_id TEXT,
    created_at TIMESTAMP
);
```

**voice_history**
```sql
CREATE TABLE voice_history (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    command TEXT,
    intent TEXT,
    response TEXT,
    audio_url TEXT,  -- optional, if retention enabled
    timestamp TIMESTAMP
);
```

---

### 7. Caching Strategy

**Redis (Optional):**
- Weather data (TTL: 5 min)
- News headlines (TTL: 15 min)
- External API responses (configurable)

**In-Memory (Dart):**
- Current user state
- Active calendar events
- Smart home device states
- Music queue

**File System:**
- Downloaded photos
- Album art
- Voice audio (if retention enabled)

---

## Communication Patterns

### REST API (Flutter ↔ Backend)

**Authentication:**
```dart
// api_service.dart
class ApiService {
  final String baseUrl;
  final String? token;
  
  Future<Map<String, dynamic>> get(String endpoint) async {
    final response = await http.get(
      Uri.parse('$baseUrl$endpoint'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );
    return jsonDecode(response.body);
  }
}
```

### WebSocket (Real-time Updates)

**Connection:**
```dart
// websocket_service.dart
class WebSocketService {
  late WebSocketChannel channel;
  
  void connect() {
    channel = WebSocketChannel.connect(
      Uri.parse('ws://localhost:8080/ws'),
    );
    channel.stream.listen((message) {
      handleMessage(jsonDecode(message));
    });
  }
  
  void handleMessage(Map<String, dynamic> data) {
    switch (data['type']) {
      case 'event_update':
        // Update calendar
        break;
      case 'smarthome_state':
        // Update device states
        break;
    }
  }
}
```

### Inter-Process Communication

**Backend Services:**
- FastAPI ↔ Rhasspy: HTTP
- FastAPI ↔ Mopidy: MPD protocol
- FastAPI ↔ Home Assistant: REST + WebSocket

---

## Deployment Architecture

### Single Device (Raspberry Pi / NUC)

```
┌─────────────────────────────────────────┐
│         Raspberry Pi 5 / NUC            │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Flutter App (Frontend)           │ │
│  │  (Runs in kiosk mode, fullscreen) │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Backend Services (Python)        │ │
│  │  • FastAPI server (port 8080)     │ │
│  │  • Rhasspy (port 12101)           │ │
│  │  • Mopidy (port 6600)             │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  Data Storage                     │ │
│  │  • SQLite database                │ │
│  │  • File system (photos, media)    │ │
│  └───────────────────────────────────┘ │
│                                         │
│  OS: Ubuntu 24.04 LTS ARM64            │
└─────────────────────────────────────────┘
```

### Distributed (Advanced)

```
┌──────────────────────┐         ┌──────────────────────┐
│  Display Device      │         │  Server (NAS/Pi)     │
│                      │         │                      │
│  Flutter App         │◄────────┤  Backend API         │
│  (Frontend only)     │  HTTP/  │  Database            │
│                      │  WSS    │  Media storage       │
└──────────────────────┘         └──────────────────────┘
                                          │
                                          ▼
                                 ┌──────────────────────┐
                                 │  External Services   │
                                 │  (Home Assistant,    │
                                 │   Calendar, etc.)    │
                                 └──────────────────────┘
```

---

## Scalability Considerations

### Multi-Display Support (Future)

**Architecture:**
- Central server (one per household)
- Multiple display clients
- Shared state via WebSocket
- Per-display user detection (face/voice)

**Synchronization:**
- Calendar/tasks: Central database
- Music: Multi-room audio (Mopidy snapcast)
- Notifications: Broadcast to all displays
- User context: Per-display tracking

---

## Security Architecture

### Authentication Flow

```
User logs in on display
    ↓
Flutter app → POST /api/auth/login {username, password}
    ↓
Backend validates credentials
    ↓
Backend generates JWT token
    ↓
Flutter stores token securely (flutter_secure_storage)
    ↓
All subsequent requests include token in headers
```

### Authorization

**Role-Based Access Control (RBAC):**
- Admin: Full access
- Adult: Standard features
- Child: Limited features (content filtering)
- Guest: Read-only, no sensitive data

### Data Encryption

**At Rest:**
- SQLite database: SQLCipher encryption
- Secure storage: flutter_secure_storage (AES-256)
- Voice recordings: Optional encryption

**In Transit:**
- HTTPS for all external APIs
- WSS (WebSocket Secure) for real-time
- Certificate pinning for critical services

---

## Monitoring & Logging

### Application Logging

**Log Levels:**
- ERROR: Critical issues
- WARN: Non-critical issues
- INFO: General info
- DEBUG: Detailed debug info

**Log Destinations:**
- File: `/var/log/kinfolk/app.log`
- Console: stdout (development)
- Remote: Optional Sentry/LogRocket (opt-in)

### Performance Monitoring

**Metrics:**
- API response times
- Voice command latency
- UI frame rate (fps)
- Memory usage
- CPU usage
- Network usage

**Tools:**
- Prometheus (optional)
- Custom dashboard in UI

---

## Backup & Disaster Recovery

### Backup Strategy

**Automatic Backups:**
```bash
#!/bin/bash
# /opt/kinfolk/backup.sh
DATE=$(date +%Y%m%d)
BACKUP_DIR="/mnt/backups/kinfolk"

# Database
sqlite3 /var/lib/kinfolk/kinfolk.db ".backup $BACKUP_DIR/kinfolk-$DATE.db"

# Photos
rsync -av /var/lib/kinfolk/photos/ $BACKUP_DIR/photos-$DATE/

# Configs
cp -r /etc/kinfolk/ $BACKUP_DIR/config-$DATE/

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "kinfolk-*" -mtime +7 -delete
```

**Schedule:** Daily at 3am (cron)

### Restore Process

```bash
# Restore from backup
kinfolk restore /path/to/backup/kinfolk-20260303.db

# Or manual restore
systemctl stop kinfolk
cp /mnt/backups/kinfolk/kinfolk-20260303.db /var/lib/kinfolk/kinfolk.db
systemctl start kinfolk
```

---

## Performance Optimization

### Frontend (Flutter)

- **Image caching:** cached_network_image
- **Lazy loading:** ListView.builder
- **Code splitting:** Deferred loading
- **Minimize rebuilds:** const constructors, memoization
- **Hardware acceleration:** Skia rendering

### Backend (Python)

- **Async I/O:** FastAPI (async/await)
- **Connection pooling:** SQLAlchemy
- **Caching:** Redis for hot data
- **Background jobs:** Celery (optional)

### Database

- **Indexes:** On frequently queried columns
- **Query optimization:** EXPLAIN QUERY PLAN
- **Vacuum:** Regular VACUUM to reclaim space

---

## Dependency Map

```
Flutter App
  ├── Riverpod (state management)
  ├── HTTP (REST client)
  ├── SQLite (local database)
  └── WebSocket (real-time)

Backend API
  ├── FastAPI (web framework)
  ├── SQLAlchemy (ORM)
  ├── Pydantic (validation)
  └── uvicorn (ASGI server)

Voice Service
  ├── Rhasspy (wake word, NLU)
  ├── PyAudio (audio recording)
  ├── Whisper API (STT)
  └── NanoTTS (TTS)

Smart Home
  └── Home Assistant (via REST API)

Music
  └── Mopidy (music server)

Calendar
  ├── caldav (CalDAV client)
  └── google-api-python-client (Google Calendar)
```

---

## Disaster Recovery Plan

**Scenarios:**

1. **App crash:** Auto-restart via systemd
2. **Database corruption:** Restore from last backup
3. **Network failure:** Graceful degradation (offline mode)
4. **Hardware failure:** Restore to new device from backup
5. **Software bug:** Rollback to previous version

---

## Version History

- **v0.1.0** - Initial architecture (March 2026)

---

*This architecture document is living and will evolve as the project matures.*
