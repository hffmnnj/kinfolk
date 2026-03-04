<p align="center">
  <h1 align="center">🏡 Kinfolk</h1>
  <p align="center"><strong>Your family's digital gathering place.</strong></p>
  <p align="center">
    An open-source, privacy-first smart display built for families — always on, always local, always yours.
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/status-in%20development-orange?style=flat-square" alt="Status" />
    <img src="https://img.shields.io/badge/version-0.1.0--alpha-blue?style=flat-square" alt="Version" />
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License" />
    <img src="https://img.shields.io/badge/flutter-desktop-54C5F8?style=flat-square&logo=flutter" alt="Flutter" />
    <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=flat-square&logo=python" alt="Python" />
  </p>
</p>

---

## What is Kinfolk?

Kinfolk is a **self-hosted smart display for your home** — think Amazon Echo Show or Magic Mirror, rebuilt from the ground up with privacy and families in mind.

Mount it in the kitchen. Leave it running. Your whole family stays in sync.

| | Kinfolk | Echo Show | Magic Mirror |
|---|---|---|---|
| Open source | ✅ | ❌ | ✅ |
| Local processing | ✅ | ❌ | ✅ |
| Family-focused UX | ✅ | Partial | ❌ |
| Voice assistant | ✅ | ✅ | Limited |
| No subscriptions | ✅ | ❌ | ✅ |
| Beautiful UI | ✅ | ✅ | Varies |

---

## Features

### Always-On Dashboard
- 🕐 **Clock & date** — always visible, elegant display
- 🌤️ **Live weather** — current conditions + forecast
- 📅 **Family calendar** — shared events, birthdays, reminders
- ✅ **To-do lists** — household tasks per family member
- 📸 **Photo frame** — rotating family memories when idle

### Voice Assistant
- 🎙️ **Wake word detection** — "Hey Kinfolk…"
- 🗣️ **Natural commands** — add events, check schedules, control music
- 🔊 **Text-to-speech** — friendly responses out loud

### Family Tools
- 👤 **Multi-user profiles** — personalized views per family member
- 🎵 **Music player** — stream local library or internet radio
- 🏠 **Smart home** — Home Assistant integration
- 📰 **News feed** — headlines from your preferred sources

### Privacy by Design
- 🔐 **100% local** — no cloud required, no data leaves your home
- 🧠 **On-device AI** — voice processing runs locally with Whisper
- 🚫 **No subscriptions** — ever

---

## Hardware

Kinfolk runs on commodity hardware you can buy today.

| Component | Recommended | Minimum |
|-----------|-------------|---------|
| Display | 1080×1920 vertical monitor | Any 1080p screen |
| Computer | Raspberry Pi 5 (8GB) | Raspberry Pi 4 (4GB) |
| Input | USB microphone | Built-in mic |
| Touch | USB touchscreen overlay | Not required |
| Camera | USB webcam (optional) | — |

> **Tip:** A vertical 27" monitor mounted in portrait mode gives the best Kinfolk experience.

---

## Tech Stack

```
┌─────────────────────────────────────┐
│           Flutter Desktop           │  ← UI layer (Linux)
├─────────────────────────────────────┤
│    FastAPI  │  SQLite  │  Whisper   │  ← Backend + AI
├─────────────────────────────────────┤
│  Rhasspy   │  Mopidy  │  HASS API  │  ← Voice, music, smart home
└─────────────────────────────────────┘
```

| Layer | Technology |
|-------|-----------|
| **Frontend** | Flutter Desktop (Linux) |
| **Backend** | Python · FastAPI · SQLAlchemy |
| **Database** | SQLite (local) · optional Supabase sync |
| **Voice** | Rhasspy (wake word) · OpenAI Whisper (STT) |
| **Music** | Mopidy |
| **Smart Home** | Home Assistant REST API |

---

## Project Structure

```
kinfolk/
├── backend/          # Python FastAPI backend
│   ├── app/          # Application code
│   └── tests/        # Backend tests
├── frontend/         # Flutter Desktop app
│   └── lib/          # Dart source code
├── .env.example      # Environment variable template
└── LICENSE
```

---

## Getting Started

> 🚧 **The project is in early development.** Full setup guides are coming soon.

**Prerequisites:**
- Python 3.11+
- Flutter 3.x (Linux desktop enabled)
- A Linux machine or Raspberry Pi

**1. Clone the repo**
```bash
git clone https://github.com/hffmnnj/kinfolk.git
cd kinfolk
```

**2. Start the backend**
```bash
cd backend
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**3. Run the frontend**
```bash
cd frontend
flutter pub get
flutter run -d linux
```

---

## Roadmap

| Milestone | Target | Status |
|-----------|--------|--------|
| Documentation & planning | March 2026 | ✅ Done |
| Dev environment & scaffolding | Mid-March 2026 | 🚧 In Progress |
| Core UI (dashboard + widgets) | Late March 2026 | ⏳ Upcoming |
| Voice integration | April 2026 | ⏳ Upcoming |
| Alpha release | May 2026 | ⏳ Upcoming |
| Beta release | July 2026 | ⏳ Upcoming |
| v1.0 public launch | September 2026 | ⏳ Upcoming |

---

## Contributing

Kinfolk is a community project and contributions are welcome!

1. **Find an issue** — look for `good first issue` labels
2. **Fork & branch** — `git checkout -b feature/your-feature`
3. **Make changes** — follow existing code style
4. **Write tests** — ensure they pass
5. **Open a PR** — describe your changes and link the issue

We're especially looking for:
- 🐦 Flutter / Dart developers
- 🐍 Python backend developers
- 🎨 UX/UI designers
- 📝 Technical writers
- 🧪 Beta testers

---

## Community

- **GitHub Issues** — [Bug reports & feature requests](https://github.com/hffmnnj/kinfolk/issues)
- **GitHub Discussions** — [Ideas & Q&A](https://github.com/hffmnnj/kinfolk/discussions)
- **Discord** — Coming soon

---

## License

MIT License — free to use, modify, and distribute. See [LICENSE](./LICENSE) for details.

---

<p align="center">
  Built with ❤️ for families who value privacy.<br/>
  <sub>© 2026 Kinfolk Contributors</sub>
</p>
