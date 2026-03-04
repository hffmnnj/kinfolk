<p align="center">
  <h1 align="center">🏡 Kinfolk</h1>
  <p align="center"><strong>Open-source, privacy-first smart family display</strong></p>
  <p align="center">
    Mount it in the kitchen. Leave it running. Your whole family stays in sync — no cloud, no subscriptions, no surveillance.
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/status-alpha-orange?style=flat-square" alt="Status" />
    <img src="https://img.shields.io/badge/version-0.1.0--alpha-blue?style=flat-square" alt="Version" />
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License" />
    <img src="https://img.shields.io/badge/flutter-desktop-54C5F8?style=flat-square&logo=flutter" alt="Flutter" />
    <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python" alt="Python" />
    <img src="https://img.shields.io/badge/platform-Raspberry%20Pi%205-C51A4A?style=flat-square" alt="Platform" />
  </p>
</p>

---

## What is Kinfolk?

Kinfolk is a **self-hosted smart display for your home** — think Amazon Echo Show or Magic Mirror, rebuilt from the ground up with privacy and families in mind.

| | Kinfolk | Echo Show | Magic Mirror |
|---|---|---|---|
| Open source | ✅ | ❌ | ✅ |
| 100% local processing | ✅ | ❌ | Partial |
| Family-focused UX | ✅ | Partial | ❌ |
| Voice assistant | ✅ | ✅ | Limited |
| No subscriptions | ✅ | ❌ | ✅ |
| Encrypted local database | ✅ | ❌ | ❌ |

---

## Features

- [x] **Clock & date** — always-on, readable from across the room
- [x] **Live weather** — current conditions via OpenWeatherMap
- [x] **Family calendar** — shared events with Google Calendar + CalDAV sync
- [x] **To-do lists** — household tasks per family member
- [x] **Voice assistant** — "Hey Kin" wake word, fully local (openWakeWord)
- [x] **Speech-to-text** — local Vosk or cloud Whisper (your choice)
- [x] **Text-to-speech** — offline NanoTTS or gTTS
- [x] **Music player** — local library via Mopidy
- [x] **Smart home** — Home Assistant WebSocket integration
- [x] **Timers & alarms** — voice-controlled, TTS alerts
- [x] **Multi-user profiles** — personalized views per family member
- [x] **Encrypted database** — SQLCipher at rest
- [x] **Photo frame** — rotating family photos when idle
- [x] **News feed** — RSS headlines

---

## Quick Start

> **Goal:** Get Kinfolk running in under 30 minutes.
> Two paths: Docker (easier) or bare-metal (more control). Both are first-class.

### Prerequisites

| Requirement | Docker path | Bare-metal path |
|-------------|-------------|-----------------|
| Git | ✅ | ✅ |
| Docker + Docker Compose | ✅ | — |
| Python 3.11+ | — | ✅ |
| Flutter 3.x (Linux desktop) | — | ✅ |
| `libgtk-3-dev`, `clang`, `cmake`, `ninja-build` | — | ✅ |

---

### Path A — Docker (Recommended for first run)

```bash
# 1. Clone
git clone https://github.com/hffmnnj/kinfolk.git
cd kinfolk

# 2. Configure
cp .env.example .env
# Edit .env — set DATABASE_ENCRYPTION_KEY and optionally OPENWEATHER_API_KEY

# 3. Start backend + services
docker compose up -d

# 4. Verify backend is healthy
curl http://localhost:8080/health
# → {"status":"healthy"}
```

Then run the Flutter frontend (Flutter cannot run inside Docker on Linux desktop):

```bash
cd frontend
flutter pub get
flutter run -d linux
```

---

### Path B — Bare Metal

```bash
# 1. Clone
git clone https://github.com/hffmnnj/kinfolk.git
cd kinfolk

# 2. System dependencies (Ubuntu/Debian)
sudo apt install -y \
  portaudio19-dev libportaudio2 libasound2-dev alsa-utils \
  libgtk-3-dev clang cmake ninja-build pkg-config \
  pipewire pipewire-pulse wireplumber

# 3. Backend
cd backend
cp .env.example .env
# Edit .env — set DATABASE_ENCRYPTION_KEY at minimum
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080

# 4. Frontend (new terminal)
cd frontend
flutter pub get
flutter run -d linux
```

**Verify everything is working:**

```bash
# Backend health
curl http://localhost:8080/health

# API docs (interactive)
open http://localhost:8080/docs
```

---

### First-Run Configuration

After starting, open `.env` (or `backend/.env`) and configure:

```bash
# Required
DATABASE_ENCRYPTION_KEY=your-secret-key-here   # Encrypt the SQLite database

# Optional but recommended
OPENWEATHER_API_KEY=your_key                    # Live weather data
HA_URL=http://homeassistant.local:8123          # Home Assistant
HA_TOKEN=your_long_lived_access_token           # HA long-lived token
```

See [`docs/configuration.md`](docs/configuration.md) for the full variable reference.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Flutter Desktop App                         │
│  Presentation → Application → Domain → Infrastructure       │
│  (Riverpod state management, Clean Architecture)            │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend (port 8080)                  │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Voice        │  │ Calendar     │  │ Music            │  │
│  │ Pipeline     │  │ Sync         │  │ (Mopidy RPC)     │  │
│  │              │  │ (Google +    │  │                  │  │
│  │ openWakeWord │  │  CalDAV)     │  │                  │  │
│  │ → STT        │  └──────────────┘  └──────────────────┘  │
│  │ → NLU        │  ┌──────────────┐  ┌──────────────────┐  │
│  │ → Dispatch   │  │ Home         │  │ Weather          │  │
│  │ → TTS        │  │ Assistant WS │  │ (OpenWeatherMap) │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                              │
│  SQLCipher (encrypted SQLite) · Users · Events · Tasks      │
└─────────────────────────────────────────────────────────────┘
```

**Stack at a glance:**

| Layer | Technology |
|-------|-----------|
| Frontend | Flutter Desktop (Dart, Riverpod, Clean Architecture) |
| Backend | Python 3.11 · FastAPI · SQLAlchemy |
| Database | SQLite encrypted with SQLCipher |
| Wake word | openWakeWord (100% local, Apache 2.0) |
| STT | Vosk (local) or OpenAI Whisper (cloud, opt-in) |
| TTS | NanoTTS (offline) or gTTS |
| Music | Mopidy (local library, JSON-RPC) |
| Smart home | Home Assistant (REST + WebSocket) |
| Calendar | Google Calendar OAuth + CalDAV |

See [`docs/architecture.md`](docs/architecture.md) for the full architecture guide.

---

## Hardware

Kinfolk is designed for a Raspberry Pi 5 with a portrait display, but runs on any Linux machine.

| Component | Recommended | Minimum |
|-----------|-------------|---------|
| Computer | Raspberry Pi 5 (8GB) | Raspberry Pi 5 (4GB) or x86-64 mini PC |
| Display | 1080×1920 portrait monitor | Any 1080p screen |
| Microphone | ReSpeaker 4-Mic Array | Any USB microphone |
| Speaker | USB or 3.5mm | Any audio output |
| Storage | 64GB microSD (A2 rated) | 32GB |
| OS | Ubuntu 24.04 LTS ARM64 | Ubuntu 22.04+ |

See [`docs/hardware-setup.md`](docs/hardware-setup.md) for the full hardware guide including portrait display configuration and kiosk mode setup.

---

## Project Structure

```
kinfolk/
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── main.py       # FastAPI app, service wiring
│   │   ├── config.py     # Settings (env-driven)
│   │   ├── database.py   # SQLAlchemy + SQLCipher
│   │   ├── models/       # ORM models
│   │   ├── schemas/      # Pydantic v2 schemas
│   │   ├── routers/      # API endpoints
│   │   └── services/     # Voice pipeline, calendar, HA, music
│   ├── rhasspy/          # NLU sentences config
│   └── requirements.txt
├── frontend/             # Flutter Desktop app
│   └── lib/
│       ├── main.dart
│       ├── presentation/ # Screens, widgets, themes
│       ├── application/  # Providers, services, use cases
│       ├── domain/       # Entities, repository interfaces
│       └── infrastructure/ # API clients, local DB
├── docker/               # Docker service configs
├── docs/                 # Developer documentation
│   ├── architecture.md
│   ├── configuration.md
│   ├── hardware-setup.md
│   └── troubleshooting.md
└── .env.example          # Environment variable template
```

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and edit.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_ENCRYPTION_KEY` | `change-me-in-env` | **Required.** SQLCipher encryption key |
| `OPENWEATHER_API_KEY` | _(empty)_ | Weather data (optional) |
| `HA_URL` | _(empty)_ | Home Assistant URL |
| `HA_TOKEN` | _(empty)_ | Home Assistant long-lived token |
| `STT_MODE` | `local` | `local` (Vosk) or `openai` (Whisper) |
| `MOPIDY_URL` | `http://localhost:6680/mopidy/rpc` | Mopidy JSON-RPC endpoint |

Full reference: [`docs/configuration.md`](docs/configuration.md)

---

## Contributing

Kinfolk is a community project and contributions are welcome!

1. **Find an issue** — look for `good first issue` labels on GitHub
2. **Fork & branch** — `git checkout -b feat/your-feature`
3. **Make changes** — follow existing code style (see `AGENTS.md`)
4. **Write tests** — `cd backend && .venv/bin/pytest tests/ -v`
5. **Lint** — `cd backend && .venv/bin/flake8 app/` and `cd frontend && flutter analyze`
6. **Open a PR** — describe your changes and link the issue

We're especially looking for:
- 🐦 Flutter / Dart developers
- 🐍 Python backend developers
- 🎨 UX/UI designers
- 📝 Technical writers
- 🧪 Beta testers (Raspberry Pi 5 hardware)

**Commit style:** `type(scope): description` (e.g. `feat(voice): add wake word sensitivity config`)

---

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/hardware-setup.md`](docs/hardware-setup.md) | Raspberry Pi 5 setup, portrait display, kiosk mode |
| [`docs/configuration.md`](docs/configuration.md) | All `.env` variables with examples |
| [`docs/architecture.md`](docs/architecture.md) | System design, voice pipeline, API reference |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Top 10 common issues and fixes |
| [`docs/compatibility.md`](docs/compatibility.md) | Dependency compatibility notes (audio, Mopidy, etc.) |

---

## Community

- **GitHub Issues** — [Bug reports & feature requests](https://github.com/hffmnnj/kinfolk/issues)
- **GitHub Discussions** — [Ideas & Q&A](https://github.com/hffmnnj/kinfolk/discussions)

---

## License

MIT License — free to use, modify, and distribute. See [LICENSE](./LICENSE) for details.

---

<p align="center">
  Built with ❤️ for families who value privacy.<br/>
  <sub>© 2026 Kinfolk Contributors</sub>
</p>
