# Kinfolk - Technical Specification

**Version:** 0.1.0-alpha  
**Last Updated:** March 2026  
**Status:** In Development

---

## Executive Summary

Kinfolk is an open-source, privacy-first smart display system designed for families. It provides a 24/7 dashboard interface combining voice control, touch interaction, and smart home integration—without the surveillance and vendor lock-in of commercial alternatives.

**Target Users:**
- Privacy-conscious families
- DIY/self-hosting enthusiasts
- Smart home users (Home Assistant, etc.)
- Households wanting shared coordination tools

**Key Differentiators:**
- 100% open-source
- Privacy-first (local processing)
- No subscriptions
- Customizable & extensible
- Multi-user family profiles

---

## System Overview

### Hardware Requirements

**Minimum Specification:**
- **Display:** 1080x1920 (portrait orientation) touchscreen
- **Computer:** Raspberry Pi 5 4GB or equivalent x86-64 mini PC
- **Microphone:** USB microphone (array recommended)
- **Speaker:** USB speaker or 3.5mm output
- **Storage:** 32GB minimum (64GB+ recommended)
- **Network:** WiFi or Ethernet
- **Optional:** USB webcam (face recognition, video calls)

**Recommended Hardware:**
```
Display:     Dell P2421D (24", 1920x1200, IPS, rotated)
             OR Asus PA248QV (24", 1920x1200, rotated)
Computer:    Raspberry Pi 5 8GB
             OR Intel NUC 11 (i3/i5)
Microphone:  ReSpeaker Mic Array v2.0
             OR PlayStation Eye Camera (modified)
Speaker:     Any USB speaker or 3.5mm
Camera:      Logitech C920 or C270 (optional)
Case:        Custom 3D-printed or wood frame
Power:       USB-C PD (Pi 5) or standard AC (NUC)
```

---

### Software Architecture

**Technology Stack:**

**Frontend:**
- **Framework:** Flutter Desktop (Linux/Windows/macOS)
- **UI Library:** Material Design 3 + custom widgets
- **State Management:** Riverpod
- **Rendering:** Skia (hardware-accelerated)

**Backend Services:**
- **Voice Processing:** Rhasspy (wake word) + Whisper API (STT)
- **Smart Home:** Home Assistant (REST API)
- **Calendar:** CalDAV + Google Calendar API
- **Music:** Mopidy + Spotify/local library
- **Database:** SQLite (local) + optional Supabase (sync)
- **Photos:** Local storage + Google Photos API

**Operating System:**
- **Primary:** Ubuntu 24.04 LTS (ARM64 for Pi, x64 for x86)
- **Alternative:** Raspberry Pi OS Lite (64-bit)
- **Desktop Environment:** Minimal (Openbox or no DE, app runs fullscreen)

**Languages:**
- Dart/Flutter (frontend)
- Python (backend services, voice processing)
- Shell scripts (system automation)

---

## System Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Display Layer                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │         Flutter Desktop Application                │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │Dashboard │ │Calendar  │ │Settings          │  │  │
│  │  │Widget    │ │View      │ │                  │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │  │
│  │  │Music     │ │Photo     │ │Voice Feedback    │  │  │
│  │  │Player    │ │Frame     │ │                  │  │  │
│  │  └──────────┘ └──────────┘ └──────────────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
│              ↕ REST API / WebSocket                      │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                   Application Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │Voice Service │  │Calendar API  │  │Media Service │   │
│  │(Python)      │  │(REST)        │  │(Mopidy)      │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │Smart Home    │  │Photo Manager │  │User Manager  │   │
│  │(HA Bridge)   │  │              │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                     Data Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │SQLite DB     │  │File Storage  │  │Config Files  │   │
│  │(local data)  │  │(photos,      │  │(YAML/JSON)   │   │
│  │              │  │ media)       │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                   External Services                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │Home Assistant│  │Google Cal    │  │OpenWeatherMap│   │
│  │(local/remote)│  │(OAuth)       │  │(API)         │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │Spotify       │  │Google Photos │  │Whisper API   │   │
│  │(OAuth)       │  │(OAuth)       │  │(OpenAI)      │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│                    Hardware Layer                         │
│  [Display] [Mic] [Speaker] [Camera] [Network] [Storage]  │
└──────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Frontend (Flutter App)

**Responsibilities:**
- UI rendering (60fps target)
- User input handling (touch, gestures)
- State management
- API communication
- Media playback (audio/video)
- Animations & transitions

**Key Features:**
- Hot reload (development)
- Cross-platform (Linux primary, Windows/macOS secondary)
- Hardware acceleration
- Responsive layouts
- Dark/light themes
- Accessibility support

**File Structure:**
```
lib/
├── main.dart                  # Entry point
├── app.dart                   # App widget
├── screens/
│   ├── dashboard_screen.dart
│   ├── calendar_screen.dart
│   ├── settings_screen.dart
│   └── ...
├── widgets/
│   ├── clock_widget.dart
│   ├── weather_widget.dart
│   ├── calendar_widget.dart
│   └── ...
├── services/
│   ├── api_service.dart       # REST API client
│   ├── voice_service.dart     # Voice interaction
│   ├── calendar_service.dart
│   └── ...
├── models/
│   ├── user.dart
│   ├── event.dart
│   ├── task.dart
│   └── ...
├── providers/
│   ├── app_state.dart         # Global state
│   ├── user_provider.dart
│   └── ...
└── utils/
    ├── constants.dart
    ├── theme.dart
    └── helpers.dart
```

---

### 2. Voice Processing Service

**Technology:** Rhasspy + Whisper API

**Pipeline:**
```
1. Wake Word Detection (Rhasspy, local)
   ↓
2. Audio Recording (3-10 seconds)
   ↓
3. Speech-to-Text (Whisper API, cloud)
   ↓
4. Intent Recognition (Rhasspy NLU, local)
   ↓
5. Command Execution
   ↓
6. Text-to-Speech Response (local TTS)
```

**Configuration:**
```yaml
# rhasspy/profile.json
{
  "wake": {
    "system": "porcupine",
    "porcupine": {
      "keyword_path": "hey_kin.ppn"
    }
  },
  "speech_to_text": {
    "system": "remote",
    "remote": {
      "url": "http://localhost:5000/stt"
    }
  },
  "intent": {
    "system": "fsticuffs"
  },
  "text_to_speech": {
    "system": "nanotts"
  }
}
```

**Intents:**
- Calendar queries
- Task management
- Weather requests
- Music control
- Smart home commands
- System controls

---

### 3. Calendar Service

**Supported Protocols:**
- CalDAV (Nextcloud, iCloud, Radicale)
- Google Calendar API
- Local SQLite storage

**Sync Strategy:**
- Pull updates every 5 minutes
- Push changes immediately
- Conflict resolution (server wins)
- Offline mode (queue changes)

**API Endpoints:**
```
GET  /api/calendar/events?start=<date>&end=<date>
POST /api/calendar/events
PUT  /api/calendar/events/{id}
DELETE /api/calendar/events/{id}
GET  /api/calendar/sources
```

---

### 4. Music Service

**Backend:** Mopidy

**Supported Sources:**
- Local files (MP3, FLAC, OGG, WAV)
- Spotify (via mopidy-spotify)
- Web radio streams
- YouTube Music (via mopidy-youtube)

**Playback Control:**
- MPD protocol (Music Player Daemon)
- REST API wrapper
- WebSocket for real-time updates

**Features:**
- Queue management
- Playlist creation
- Search
- Favorites
- Recently played

---

### 5. Smart Home Integration

**Backend:** Home Assistant

**Communication:**
- REST API
- WebSocket (real-time updates)
- MQTT (optional)

**Entity Types:**
- Lights (on/off, brightness, color)
- Switches
- Sensors
- Climate (thermostats)
- Locks
- Cameras
- Media players

**API Examples:**
```python
# Turn on light
POST /api/services/light/turn_on
{
  "entity_id": "light.living_room",
  "brightness": 255
}

# Get state
GET /api/states/light.living_room

# Subscribe to updates
WS: {"type": "subscribe_events", "event_type": "state_changed"}
```

---

## Data Models

### User
```dart
class User {
  String id;
  String name;
  String? email;
  UserRole role; // admin, adult, child, guest
  String? profilePhoto;
  Map<String, dynamic> preferences;
  DateTime createdAt;
  DateTime lastActive;
}
```

### Event (Calendar)
```dart
class Event {
  String id;
  String userId; // owner
  String title;
  DateTime startTime;
  DateTime endTime;
  String? location;
  String? description;
  List<String> attendees;
  String? recurrence; // RRULE
  List<Reminder> reminders;
  String color;
}
```

### Task
```dart
class Task {
  String id;
  String userId; // assigned to
  String title;
  String? description;
  DateTime? dueDate;
  TaskPriority priority;
  bool completed;
  String listId; // shopping, chores, etc.
  DateTime createdAt;
}
```

### SmartHomeDevice
```dart
class SmartHomeDevice {
  String entityId;
  String name;
  String type; // light, switch, sensor, etc.
  Map<String, dynamic> state;
  Map<String, dynamic> attributes;
  DateTime lastUpdated;
}
```

---

## API Specification

### REST API

**Base URL:** `http://localhost:8080/api/v1`

**Authentication:** JWT tokens (for remote access)

**Endpoints:**

**Users**
```
GET    /users
GET    /users/{id}
POST   /users
PUT    /users/{id}
DELETE /users/{id}
```

**Calendar**
```
GET    /calendar/events
POST   /calendar/events
PUT    /calendar/events/{id}
DELETE /calendar/events/{id}
GET    /calendar/sources
```

**Tasks**
```
GET    /tasks
POST   /tasks
PUT    /tasks/{id}
DELETE /tasks/{id}
GET    /tasks/lists
```

**Voice**
```
POST   /voice/command
GET    /voice/history
POST   /voice/tts
```

**Smart Home**
```
GET    /smarthome/devices
POST   /smarthome/devices/{id}/command
GET    /smarthome/scenes
POST   /smarthome/scenes/{id}/activate
```

**Media**
```
GET    /media/music/search?q={query}
POST   /media/music/play
POST   /media/music/pause
POST   /media/music/next
GET    /media/photos
POST   /media/photos/slideshow/start
```

**Response Format:**
```json
{
  "status": "success",
  "data": { ... },
  "timestamp": "2026-03-03T22:00:00Z"
}
```

**Error Format:**
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_INPUT",
    "message": "User-friendly error message",
    "details": { ... }
  },
  "timestamp": "2026-03-03T22:00:00Z"
}
```

---

## Security & Privacy

### Data Storage

**Local Data:**
- All user data stored locally by default
- SQLite database encrypted at rest (SQLCipher)
- No telemetry or analytics
- No data sent to cloud without explicit consent

**Optional Cloud Sync:**
- End-to-end encrypted (user controls keys)
- Supabase backend (self-hostable)
- Explicit opt-in only

### Voice Processing

**Wake Word:**
- 100% local processing (Porcupine/Rhasspy)
- No audio sent to network until wake word detected

**Speech-to-Text:**
- Can be configured as local-only (slower, less accurate)
- OR cloud (Whisper API, encrypted in transit)
- User choice during setup

**Audio Retention:**
- Voice commands NOT stored by default
- Optional: Keep last 24h for debugging
- User can delete all audio data

### Network Security

- HTTPS for all external API calls
- Certificate pinning for critical services
- Local-first: Works without internet
- Optional VPN support
- Firewall rules (only necessary ports)

### Camera & Face Recognition

- Camera can be physically disabled (shutter)
- Face recognition 100% local (no cloud)
- Face data stored encrypted
- User can delete all face data
- Visual indicator when camera active

---

## Performance Requirements

### Response Times

- Touch interaction: < 50ms
- Voice wake word detection: < 500ms
- Voice command execution: < 2s (STT + processing)
- Calendar updates: < 1s
- UI animations: 60fps
- Music playback: Instant (< 100ms)

### Resource Usage

**Raspberry Pi 5 4GB:**
- CPU: < 50% average, < 80% peak
- RAM: < 2GB (leave 2GB for system)
- Storage: < 10GB (app + cache)
- Network: < 1Mbps average

**Display:**
- Brightness auto-adjust (energy saving)
- Screen timeout after 30min idle
- Screensaver mode (dim, minimal)

---

## Testing Strategy

### Unit Tests

- All business logic
- Data models
- API clients
- State management

**Target:** 80% code coverage

### Integration Tests

- API endpoints
- Database operations
- External service mocks

### UI Tests

- Widget tests (Flutter)
- Golden tests (screenshot comparisons)
- Interaction tests

### End-to-End Tests

- Full user flows
- Voice command scenarios
- Multi-user interactions

### Manual Testing

- Hardware compatibility
- Performance on target devices
- Voice accuracy
- UX validation

---

## Deployment

### Installation Methods

**1. Pre-built Image (Easiest)**
```bash
# Flash SD card with Kinfolk OS image
dd if=kinfolk-rpi5-v0.1.0.img of=/dev/sdX bs=4M
```

**2. Package Manager**
```bash
# Ubuntu/Debian
sudo apt install kinfolk

# Arch Linux
yay -S kinfolk
```

**3. Docker**
```bash
docker pull kinfolk/kinfolk:latest
docker run -d -p 8080:8080 kinfolk/kinfolk
```

**4. Build from Source**
```bash
git clone https://github.com/yourusername/kinfolk.git
cd kinfolk
./install.sh
```

### Configuration

**First-run Setup:**
1. Connect to WiFi
2. Create admin user
3. Configure calendar sources
4. Set up voice assistant
5. Connect smart home (optional)
6. Add family members

**Config Files:**
```
~/.config/kinfolk/
├── config.yaml         # Main config
├── users.db            # SQLite database
├── calendars.yaml      # Calendar sources
├── voice.yaml          # Voice settings
└── smarthome.yaml      # HA connection
```

---

## Maintenance & Updates

### Automatic Updates

- Check for updates daily
- Download in background
- Install during idle time (3am default)
- Rollback if update fails
- User notification before major updates

### Backup & Restore

**Automated Backups:**
- Daily local backup
- Optional cloud backup (encrypted)
- Last 7 days retained

**Manual Backup:**
```bash
kinfolk backup create /path/to/backup.tar.gz
kinfolk backup restore /path/to/backup.tar.gz
```

### Monitoring

- System health dashboard
- Error logging
- Performance metrics
- Optional Sentry integration (opt-in)

---

## Accessibility

### Visual

- High contrast mode
- Adjustable font sizes (150%, 200%)
- Color blind friendly palette
- Screen reader support (planned)

### Motor

- Large touch targets (min 44x44pt)
- Simplified navigation
- Voice-only mode (no touch required)
- Custom gesture sensitivity

### Cognitive

- Simple, clear UI
- Consistent layouts
- Visual feedback for actions
- Error messages in plain language

---

## Localization

### Supported Languages (Phase 1)

- English (US, UK)
- Spanish
- French
- German

### i18n Framework

- Flutter's intl package
- ARB files for translations
- RTL support (Arabic, Hebrew)
- Date/time localization
- Number formatting

---

## Documentation

### User Documentation

- Setup guide
- User manual
- FAQ
- Troubleshooting
- Video tutorials

### Developer Documentation

- API reference
- Architecture guide
- Plugin development
- Contributing guide
- Code style guide

---

## Success Metrics

### Key Performance Indicators

**Technical:**
- App crash rate < 0.1%
- Voice accuracy > 90%
- API response time < 500ms
- Uptime > 99%

**User Experience:**
- Setup time < 15 minutes
- Daily active usage > 10 interactions
- User retention > 80% after 30 days

**Community:**
- GitHub stars (target: 1,000 in year 1)
- Contributors (target: 50 in year 1)
- Discord members (target: 500 in year 1)

---

## Roadmap

**Q2 2026 (Current):**
- [x] Technical specification
- [ ] Core dashboard UI
- [ ] Voice integration (basic)
- [ ] Calendar & tasks
- [ ] Alpha release (developers only)

**Q3 2026:**
- [ ] Beta release
- [ ] Music player
- [ ] Photo frame
- [ ] Smart home integration
- [ ] Multi-user profiles
- [ ] Public release (v1.0)

**Q4 2026:**
- [ ] Plugin system
- [ ] Mobile companion app
- [ ] Video calls
- [ ] Advanced automations
- [ ] Community marketplace

**2027:**
- [ ] Multi-display sync
- [ ] Advanced AI features
- [ ] Hardware partnerships
- [ ] Enterprise features

---

## Contributing

See CONTRIBUTING.md for:
- Code of conduct
- Development setup
- Coding standards
- PR process
- Testing requirements

---

## License

MIT License - See LICENSE file for details

---

**Document Version:** 0.1.0  
**Last Updated:** March 3, 2026  
**Maintainer:** [Your Name]  
**Contact:** [Your Email]

