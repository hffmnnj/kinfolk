# Configuration Reference

All Kinfolk configuration is driven by environment variables. Copy `.env.example` to `.env` (in the project root or `backend/`) and edit the values.

```bash
cp .env.example .env
```

The backend reads `.env` automatically via `pydantic-settings`. Variables set in the shell environment take precedence over the file.

---

## Quick Setup

Minimum required configuration to get Kinfolk running:

```bash
# backend/.env (or root .env)

# REQUIRED: Encrypt the local database
DATABASE_ENCRYPTION_KEY=replace-with-a-long-random-secret

# OPTIONAL but recommended
OPENWEATHER_API_KEY=your_openweathermap_key
```

Everything else has sensible defaults for local development.

---

## Variable Reference

### Application

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `APP_NAME` | `Kinfolk API` | No | Application name shown in API docs |
| `APP_VERSION` | `0.1.0` | No | Version string |
| `DEBUG` | `false` | No | Enable debug mode (verbose logging, auto-reload) |

### Server

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `HOST` | `0.0.0.0` | No | Interface to bind. Use `127.0.0.1` to restrict to localhost |
| `PORT` | `8080` | No | Port for the FastAPI server |

**Example:**
```bash
HOST=127.0.0.1
PORT=8080
```

### Database

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | `sqlite:///./kinfolk.db` | No | SQLAlchemy database URL. Relative paths are relative to `backend/` |
| `DATABASE_ENCRYPTION_KEY` | `change-me-in-env` | **Yes** | SQLCipher encryption key. Use a long random string. Changing this after first run requires re-encrypting the database |

**Example:**
```bash
DATABASE_URL=sqlite:///./kinfolk.db
DATABASE_ENCRYPTION_KEY=xK9mP2qR7vL4nJ8wA3cF6hD1tY5uB0eG
```

> **Security note:** The encryption key is used to encrypt the SQLite database at rest via SQLCipher. Treat it like a password — store it securely and don't commit it to version control.

### CORS

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000","http://localhost:8080","http://127.0.0.1:8080"]` | No | JSON array of allowed origins for the Flutter app |
| `CORS_ALLOW_ALL` | `false` | No | Set `true` to allow all origins (development only — never in production) |

**Example:**
```bash
CORS_ORIGINS=["http://localhost:3000","http://192.168.1.100:3000"]
```

### Weather

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `OPENWEATHER_API_KEY` | _(empty)_ | No | [OpenWeatherMap](https://openweathermap.org/api) API key. Free tier is sufficient. Without this, weather shows placeholder data |
| `WEATHER_CITY` | `San Francisco` | No | Default city for weather lookups |
| `WEATHER_UNITS` | `imperial` | No | `imperial` (°F) or `metric` (°C) |

**Example:**
```bash
OPENWEATHER_API_KEY=abc123def456
WEATHER_CITY=London
WEATHER_UNITS=metric
```

### Google Calendar

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `GOOGLE_CLIENT_ID` | _(empty)_ | No | OAuth 2.0 client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | _(empty)_ | No | OAuth 2.0 client secret |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8080/api/v1/auth/google/callback` | No | OAuth callback URL. Must match what's configured in Google Cloud Console |

**Setup steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable Google Calendar API
3. Create OAuth 2.0 credentials (Desktop app type)
4. Add `http://localhost:8080/api/v1/auth/google/callback` as an authorized redirect URI

**Example:**
```bash
GOOGLE_CLIENT_ID=123456789-abc.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123
GOOGLE_REDIRECT_URI=http://localhost:8080/api/v1/auth/google/callback
```

### CalDAV

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `CALDAV_SERVERS` | `[]` | No | JSON array of CalDAV server configs. Supports Nextcloud, iCloud, Radicale, and any standard CalDAV server |

**Format:**
```bash
CALDAV_SERVERS='[
  {
    "url": "https://nextcloud.example.com/remote.php/dav/",
    "username": "alice",
    "password": "app-password-here",
    "calendar_name": "personal"
  }
]'
```

> **Tip:** Use app-specific passwords (not your main account password) for CalDAV connections. Nextcloud, iCloud, and most providers support this.

### Voice — Wake Word

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `WAKE_WORD_ENGINE` | `openwakeword` | No | Wake word engine. Currently only `openwakeword` is supported |
| `WAKE_WORD_SENSITIVITY` | `0.5` | No | Detection sensitivity (0.0–1.0). Higher = more sensitive but more false positives |
| `AUDIO_SAMPLE_RATE` | `16000` | No | Microphone sample rate in Hz. 16000 is standard for voice |
| `AUDIO_CHANNELS` | `1` | No | Number of audio channels. `1` (mono) is recommended for voice |

**Example:**
```bash
WAKE_WORD_ENGINE=openwakeword
WAKE_WORD_SENSITIVITY=0.6
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
```

### Voice — Speech-to-Text (STT)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `STT_MODE` | `local` | No | `local` uses Vosk (offline, no API key needed). `openai` uses Whisper API (requires `OPENAI_API_KEY`, better accuracy) |
| `VOSK_MODEL_PATH` | `./models/vosk-model-en-us` | No | Path to the Vosk model directory. Download from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) |
| `OPENAI_API_KEY` | _(empty)_ | No | OpenAI API key. Required only when `STT_MODE=openai` |

**Example (local, offline):**
```bash
STT_MODE=local
VOSK_MODEL_PATH=./models/vosk-model-en-us-0.22
```

**Example (cloud Whisper):**
```bash
STT_MODE=openai
OPENAI_API_KEY=sk-proj-abc123
```

> **Privacy note:** With `STT_MODE=local`, all voice processing stays on-device. With `STT_MODE=openai`, audio is sent to OpenAI after the wake word is detected.

### Voice — Text-to-Speech (TTS)

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `TTS_ENGINE` | `nanotts` | No | `nanotts` for offline TTS (requires NanoTTS installed). `gtts` for Google TTS (requires internet) |
| `TTS_SPEED` | `1.0` | No | Speech speed multiplier (0.5–2.0) |
| `TTS_VOLUME` | `0.8` | No | TTS output volume (0.0–1.0) |

**Example:**
```bash
TTS_ENGINE=nanotts
TTS_SPEED=1.0
TTS_VOLUME=0.8
```

**Install NanoTTS (offline TTS):**
```bash
sudo apt install -y nanotts
```

### Voice — NLU

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NLU_CONFIDENCE_THRESHOLD` | `0.5` | No | Minimum confidence score (0.0–1.0) for intent recognition. Commands below this threshold are rejected |
| `SENTENCES_INI_PATH` | `./backend/rhasspy/sentences.ini` | No | Path to the Rhasspy-format sentences file defining voice command patterns |

### Music

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `MOPIDY_URL` | `http://localhost:6680/mopidy/rpc` | No | Mopidy JSON-RPC endpoint. Change host if Mopidy runs on a different machine or Docker container |

**Example:**
```bash
MOPIDY_URL=http://localhost:6680/mopidy/rpc
```

**Install Mopidy:**
```bash
sudo apt install -y mopidy gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly

# Configure music directory (~/.config/mopidy/mopidy.conf)
[local]
media_dir = /home/kinfolk/Music

[http]
hostname = 0.0.0.0
port = 6680
```

### Smart Home

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `HA_URL` | _(empty)_ | No | Home Assistant base URL (e.g. `http://homeassistant.local:8123` or `https://your-ha.duckdns.org`) |
| `HA_TOKEN` | _(empty)_ | No | Home Assistant long-lived access token. Generate in HA: Profile → Long-Lived Access Tokens |

**Example:**
```bash
HA_URL=http://homeassistant.local:8123
HA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Generate a HA token:**
1. Open Home Assistant → click your profile (bottom left)
2. Scroll to **Long-Lived Access Tokens**
3. Click **Create Token**, give it a name (e.g. "Kinfolk")
4. Copy the token — it's only shown once

### Photos

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PHOTOS_DIRECTORY` | `~/Pictures` | No | Local directory for the photo frame slideshow. Supports `~` expansion |

**Example:**
```bash
PHOTOS_DIRECTORY=/home/kinfolk/Photos
```

---

## Complete .env Example

```bash
# ── Application ──────────────────────────────────────────────
APP_NAME=Kinfolk API
APP_VERSION=0.1.0
DEBUG=false

# ── Server ───────────────────────────────────────────────────
HOST=0.0.0.0
PORT=8080

# ── Database ─────────────────────────────────────────────────
DATABASE_URL=sqlite:///./kinfolk.db
DATABASE_ENCRYPTION_KEY=replace-with-a-long-random-secret-here

# ── CORS ─────────────────────────────────────────────────────
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]
CORS_ALLOW_ALL=false

# ── Weather ──────────────────────────────────────────────────
OPENWEATHER_API_KEY=your_openweathermap_key
WEATHER_CITY=New York
WEATHER_UNITS=imperial

# ── Google Calendar ──────────────────────────────────────────
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8080/api/v1/auth/google/callback

# ── CalDAV ───────────────────────────────────────────────────
CALDAV_SERVERS=[]

# ── Voice: Wake Word ─────────────────────────────────────────
WAKE_WORD_ENGINE=openwakeword
WAKE_WORD_SENSITIVITY=0.5
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1

# ── Voice: STT ───────────────────────────────────────────────
STT_MODE=local
VOSK_MODEL_PATH=./models/vosk-model-en-us-0.22
OPENAI_API_KEY=

# ── Voice: TTS ───────────────────────────────────────────────
TTS_ENGINE=nanotts
TTS_SPEED=1.0
TTS_VOLUME=0.8

# ── Voice: NLU ───────────────────────────────────────────────
NLU_CONFIDENCE_THRESHOLD=0.5
SENTENCES_INI_PATH=./backend/rhasspy/sentences.ini

# ── Music ────────────────────────────────────────────────────
MOPIDY_URL=http://localhost:6680/mopidy/rpc

# ── Smart Home ───────────────────────────────────────────────
HA_URL=http://homeassistant.local:8123
HA_TOKEN=

# ── Photos ───────────────────────────────────────────────────
PHOTOS_DIRECTORY=~/Pictures
```

---

## Generating a Secure Encryption Key

```bash
# Generate a 32-byte random key (recommended)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Or with openssl
openssl rand -hex 32
```

---

## Environment Variable Precedence

1. Shell environment variables (highest priority)
2. `.env` file in `backend/`
3. `.env` file in project root
4. Default values in `config.py` (lowest priority)

---

## Validating Configuration

Start the backend and check the health endpoint:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --port 8080

# In another terminal
curl http://localhost:8080/health
# → {"status":"healthy"}

# View all loaded settings (debug mode only)
curl http://localhost:8080/docs
```

If the backend fails to start, check the error output — missing required variables or invalid values will be reported clearly by pydantic-settings.
