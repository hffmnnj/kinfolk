# AGENTS.md — Kinfolk

Developer and agent reference for the Kinfolk project.

---

## Project Overview

Kinfolk is an open-source, privacy-first smart display for families. It runs on a Raspberry Pi 5 or mini PC with a 1080×1920 portrait touchscreen. The stack is Flutter Desktop (frontend) + Python FastAPI (backend) + SQLite (database).

---

## Commands (Auto)

Verified commands from Milestone 2 & 3 execution.

### Frontend (Flutter)

```bash
# Run on Linux desktop
cd frontend && flutter run -d linux

# Analyze (lint)
cd frontend && flutter analyze

# Tests
cd frontend && flutter test

# Install dependencies
cd frontend && flutter pub get
```

### Backend (Python)

```bash
# Activate virtual environment
cd backend && source .venv/bin/activate

# Install dependencies
cd backend && pip install -r requirements.txt

# Start dev server
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8080

# Lint
cd backend && .venv/bin/flake8 app/

# Tests
cd backend && .venv/bin/pytest tests/ -v

# Health check (server must be running)
curl http://localhost:8080/health
```

### Git

```bash
# Current branch
git branch --show-current   # feat/kinfolk-initial-build

# Remote
git remote -v               # https://github.com/hffmnnj/kinfolk.git
```

---

## Architecture (Auto)

### Directory Structure

```
kinfolk/
├── frontend/               # Flutter Desktop app (Dart)
│   └── lib/
│       ├── main.dart       # Entry point — ProviderScope + MaterialApp
│       ├── presentation/   # UI layer (screens, widgets, themes)
│       ├── application/    # Business logic (providers, services, use_cases)
│       ├── domain/         # Core entities and repository interfaces
│       └── infrastructure/ # External integrations (API, database)
├── backend/                # Python FastAPI backend
│   └── app/
│       ├── main.py         # FastAPI app, CORS, router registration
│       ├── config.py       # Settings (env-driven, no hardcoded secrets)
│       ├── database.py     # SQLAlchemy engine, session, Base
│       ├── models/         # ORM models (User, Event, Task, VoiceHistory)
│       ├── schemas/        # Pydantic v2 schemas (Create/Update/Response)
│       ├── routers/        # API routers (users, calendar, tasks, voice, smarthome)
│       └── tests/          # pytest tests
└── .env.example            # Environment variable template
```

### API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check → `{"status": "healthy"}` |
| `/api/v1/users` | CRUD | User management |
| `/api/v1/calendar` | CRUD | Calendar events |
| `/api/v1/tasks` | CRUD | Task lists |
| `/api/v1/voice` | CRUD | Voice history |
| `/api/v1/smarthome` | CRUD | Smart home control |

**API response format:**
```json
{ "status": "success", "data": {}, "timestamp": "..." }
```

**Base URL (local dev):** `http://localhost:8080/api/v1`

### Database Schema

Four SQLite tables, auto-created on startup via `Base.metadata.create_all()`:
- `users` — id, name, email, role, preferences (JSON), created_at, last_active
- `events` — id, user_id FK, title, start_time, end_time, location, attendees (JSON)
- `tasks` — id, user_id FK, title, description, due_date, priority, completed
- `voice_history` — id, user_id FK, command, intent, response, timestamp

---

## Design System (Auto)

### Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `KinfolkColors.warmClay` | `#D4A574` | Primary accent |
| `KinfolkColors.deepCharcoal` | `#2A2A2E` | Dark background |
| `KinfolkColors.softCream` | `#F5F3ED` | Light background / dark text |
| `KinfolkColors.forestGreen` | `#4A7C59` | Success / secondary |
| `KinfolkColors.skyBlue` | `#7BA7BC` | Info / tertiary |
| `KinfolkColors.sunsetOrange` | `#E07856` | Warning / error |
| `KinfolkColors.sageGray` | `#9CA3A8` | Muted / dividers |

### Typography (Inter, bundled)

| Style key | Size | Weight | Usage |
|-----------|------|--------|-------|
| `displayLarge` | 48px | 600 | Clock, hero numbers |
| `displayMedium` | 36px | 600 | Page titles (H1) |
| `displaySmall` | 28px | 600 | Section headers (H2) |
| `headlineLarge` | 22px | 500 | Sub-headers (H3) |
| `bodyLarge` | 16px | 400 | Body text |
| `bodyMedium` | 14px | 400 | Secondary text |
| `bodySmall` | 12px | 400 | Captions |
| `labelLarge` | 14px | 500 | Buttons, labels |

### Themes

```dart
// Apply themes in MaterialApp
theme: KinfolkTheme.light,
darkTheme: KinfolkTheme.dark,
themeMode: ThemeMode.dark,  // Dark by default
```

---

## Gotchas (Auto)

- **GTK headers needed for Flutter Linux.** `flutter analyze` works without them; `flutter run -d linux` requires `libgtk-3-dev`, `clang`, `cmake`, `ninja-build`, `pkg-config`. Install with: `sudo apt install libgtk-3-dev clang cmake ninja-build pkg-config`

- **AUR Flutter SDK constraint** may generate `sdk: ^3.10.1` or higher. Relax to `^3.7.0` if the official Flutter stable channel version is lower.

- **CORS wildcard + credentials is a FastAPI runtime error.** Never use `allow_origins=["*"]` with `allow_credentials=True`. Use settings-driven origins (see `backend/app/config.py`).

- **google_fonts fetches at runtime from Google CDN.** For privacy-first/offline use, always bundle fonts as TTF assets and declare them in `pubspec.yaml`. See `frontend/assets/fonts/`.

- **pubspec.lock should be committed** for Flutter app projects (not libraries). This ensures reproducible builds. The `.gitignore` was updated to not exclude `pubspec.lock`.

- **Backend virtual env is `.venv/` inside `backend/`.** Always prefix commands with `.venv/bin/` or activate first.

- **Dashboard overflow on landscape.** The app targets portrait 1080×1920. On landscape/dev screens, wrap scrollable sections in `SingleChildScrollView` to avoid overflow errors.

- **Fullscreen kiosk mode:** Set in `frontend/linux/runner/my_application.cc` — `gtk_window_set_decorated(window, FALSE)` + `gtk_window_fullscreen(window)`. Do not add a window title or decorations.

---

## Conventions (Auto)

| Aspect | Standard |
|--------|----------|
| Dart files | `snake_case` (e.g. `dashboard_screen.dart`) |
| Python files | `snake_case` (e.g. `calendar_service.py`) |
| Flutter tests | `*_test.dart` |
| Python tests | `test_*.py` |
| Commits | Conventional commits: `type(scope): description` |
| Branches | `feat/`, `fix/`, `refactor/`, `chore/` prefixes |
| State management | Riverpod only — no `setState()` |
| Layer boundary | Domain layer must NOT import from Infrastructure layer |

---

*Auto-generated by GoopSpec v0.2.8 after Milestone 2 & 3 acceptance on 2026-03-04*
