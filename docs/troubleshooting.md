# Troubleshooting

Common issues and how to fix them. If your issue isn't listed here, check [GitHub Issues](https://github.com/hffmnnj/kinfolk/issues) or open a new one.

---

## 1. SQLCipher binding not found

**Symptom:**
```
ImportError: No module named 'sqlcipher3'
# or
sqlalchemy.exc.OperationalError: (sqlcipher3.dbapi2.OperationalError) file is not a database
```

**Cause:** The `sqlcipher3` Python package requires the system SQLCipher library headers to build. Either the headers are missing, or the package was installed before the headers were present.

**Fix:**

```bash
# 1. Install system SQLCipher library
sudo apt install -y libsqlcipher-dev sqlcipher

# 2. Reinstall the Python binding (force rebuild)
source backend/.venv/bin/activate
pip uninstall -y sqlcipher3
pip install --no-cache-dir sqlcipher3

# 3. Verify
python3 -c "import sqlcipher3; print('OK')"
```

**If the wheel still fails to build on ARM64:**

```bash
# Try the alternative pysqlcipher3 package
pip install pysqlcipher3

# Or build sqlcipher3 from source with explicit library path
LDFLAGS="-L/usr/lib/aarch64-linux-gnu" \
CFLAGS="-I/usr/include" \
pip install --no-binary sqlcipher3 sqlcipher3
```

**Note:** If you change `DATABASE_ENCRYPTION_KEY` after the database has been created, the existing database cannot be opened. Either delete `backend/kinfolk.db` (loses all data) or re-encrypt it with `sqlcipher`:

```bash
sqlcipher backend/kinfolk.db
sqlite> PRAGMA rekey='new-key-here';
sqlite> .quit
```

---

## 2. Wake word not detecting

**Symptom:** Saying "Hey Kin" does nothing. No response, no log output.

**Diagnosis steps:**

```bash
# 1. Check if the microphone is detected
arecord -l
# Should list your USB mic. If empty, the mic isn't recognized.

# 2. Test recording
arecord -d 3 -f cd -r 16000 /tmp/test.wav
aplay /tmp/test.wav
# You should hear your voice played back.

# 3. Check backend logs for wake word service errors
cd backend && source .venv/bin/activate
uvicorn app.main:app --port 8080 --log-level debug 2>&1 | grep -i "wake\|audio\|sound"
```

**Fix — microphone not detected:**

```bash
# Check PipeWire is running
systemctl --user status pipewire pipewire-pulse

# Restart PipeWire if needed
systemctl --user restart pipewire pipewire-pulse wireplumber

# Verify mic appears
pactl list sources short
```

**Fix — wrong audio device:**

```bash
# List devices with indices
python3 -c "import sounddevice; print(sounddevice.query_devices())"

# Set the correct device index in .env
AUDIO_DEVICE_INDEX=1   # replace with your device index
```

**Fix — sensitivity too low:**

```bash
# Increase sensitivity in .env (range: 0.0–1.0)
WAKE_WORD_SENSITIVITY=0.7
```

**Fix — openWakeWord model not downloaded:**

```bash
# The model downloads automatically on first run, but may fail without internet
# Manually trigger download
python3 -c "from openwakeword.model import Model; Model()"
```

---

## 3. Flutter Linux build dependencies missing

**Symptom:**
```
CMake Error: Could not find a package configuration file provided by "PkgConfig"
# or
/usr/bin/ld: cannot find -lgtk-3
# or
flutter run -d linux fails with clang/cmake errors
```

**Fix:**

```bash
# Install all Flutter Linux build dependencies
sudo apt install -y \
  libgtk-3-dev \
  clang \
  cmake \
  ninja-build \
  pkg-config \
  liblzma-dev \
  libstdc++-12-dev

# Verify Flutter can find them
flutter doctor -v
# Should show "Linux toolchain - develop for Linux desktop" as OK
```

**If `flutter analyze` works but `flutter run -d linux` fails:**

The GTK headers are only needed for the native build, not for analysis. Install `libgtk-3-dev` and retry.

**AUR Flutter SDK constraint issue (Arch Linux):**

If `pubspec.yaml` shows `sdk: ^3.10.1` but your Flutter is older:

```yaml
# frontend/pubspec.yaml — relax the constraint
environment:
  sdk: ^3.7.0
```

---

## 4. Mopidy not connecting

**Symptom:**
```
httpx.ConnectError: [Errno 111] Connection refused
# or
MopidyMusicService: Failed to connect to http://localhost:6680/mopidy/rpc
```

**Cause:** Mopidy isn't running, or it's listening on a different port/interface.

**Fix — start Mopidy:**

```bash
# Install if not present
sudo apt install -y mopidy gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly

# Start Mopidy
mopidy &

# Or as a systemd service
sudo systemctl enable --now mopidy
```

**Fix — configure Mopidy to listen on HTTP:**

Edit `~/.config/mopidy/mopidy.conf`:

```ini
[http]
enabled = true
hostname = 127.0.0.1
port = 6680
```

Restart Mopidy and verify:

```bash
curl http://localhost:6680/mopidy/rpc \
  -d '{"jsonrpc":"2.0","id":1,"method":"core.get_version"}' \
  -H 'Content-Type: application/json'
# → {"jsonrpc":"2.0","id":1,"result":"3.x.x"}
```

**Fix — Mopidy in Docker needs audio access:**

```bash
docker run -d \
  --name mopidy \
  --device /dev/snd:/dev/snd \
  -v /run/user/$(id -u)/pulse:/run/user/1000/pulse \
  -e PULSE_SERVER=unix:/run/user/1000/pulse/native \
  -p 6680:6680 \
  mopidy/mopidy
```

---

## 5. Home Assistant token invalid

**Symptom:**
```
homeassistant: 401 Unauthorized
# or
HomeAssistantService: Authentication failed
```

**Cause:** The `HA_TOKEN` in `.env` is wrong, expired, or the HA URL is unreachable.

**Fix — generate a new token:**

1. Open Home Assistant in your browser
2. Click your profile icon (bottom left sidebar)
3. Scroll to **Long-Lived Access Tokens**
4. Click **Create Token**, name it "Kinfolk"
5. Copy the token immediately (shown only once)
6. Update `.env`:

```bash
HA_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Fix — verify HA is reachable:**

```bash
# Test connectivity
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://homeassistant.local:8123/api/

# Should return: {"message": "API running."}
```

**Fix — HA URL format:**

```bash
# Correct formats
HA_URL=http://homeassistant.local:8123
HA_URL=http://192.168.1.100:8123
HA_URL=https://your-ha.duckdns.org

# Wrong (trailing slash causes issues)
HA_URL=http://homeassistant.local:8123/   # ← remove trailing slash
```

---

## 6. openWakeWord model not found

**Symptom:**
```
FileNotFoundError: Model file not found: hey_kin.tflite
# or
openwakeword: No models loaded
```

**Cause:** The custom wake word model file isn't present, or the path is wrong.

**Fix — use the built-in models (quickest):**

openWakeWord ships with several pre-trained models. Use one while you train a custom "Hey Kin" model:

```python
# Test with built-in "hey_jarvis" model
from openwakeword.model import Model
m = Model(wakeword_models=["hey_jarvis"])
```

**Fix — download/train a custom model:**

```bash
# Install training dependencies
pip install openwakeword[train]

# Generate training data and train (see openWakeWord docs)
# https://github.com/dscripka/openWakeWord#training-new-models

# Place the .tflite model file in:
mkdir -p backend/models/wake_words/
cp hey_kin.tflite backend/models/wake_words/
```

**Fix — verify model path in config:**

The wake word service looks for models in the directory specified at startup. Check the backend logs for the exact path it's searching.

---

## 7. PipeWire / PulseAudio microphone issues

**Symptom:** Microphone is detected by `arecord -l` but the Python backend can't access it, or audio is choppy/silent.

**Fix — restart PipeWire:**

```bash
systemctl --user restart pipewire pipewire-pulse wireplumber
```

**Fix — check for permission issues:**

```bash
# Add your user to the audio group
sudo usermod -aG audio $USER
# Log out and back in for this to take effect

# Verify
groups | grep audio
```

**Fix — USB mic hot-plug:**

If you plugged in the mic after boot:

```bash
# Trigger device re-scan
pactl load-module module-udev-detect
```

**Fix — Docker containers can't access audio:**

Services in Docker need explicit audio device access:

```yaml
# docker-compose.yml
services:
  wake-word:
    image: rhasspy/wyoming-openwakeword
    devices:
      - /dev/snd:/dev/snd
    volumes:
      - /run/user/1000/pulse:/run/user/1000/pulse
    environment:
      - PULSE_SERVER=unix:/run/user/1000/pulse/native
```

**Fix — check sounddevice can see the mic:**

```bash
source backend/.venv/bin/activate
python3 -c "
import sounddevice as sd
print(sd.query_devices())
print('Default input:', sd.default.device[0])
"
```

---

## 8. Google Calendar OAuth callback failing

**Symptom:**
```
redirect_uri_mismatch
# or
Error 400: redirect_uri_mismatch
```

**Cause:** The redirect URI in your Google Cloud Console credentials doesn't match `GOOGLE_REDIRECT_URI` in `.env`.

**Fix:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → Your project → APIs & Services → Credentials
2. Click your OAuth 2.0 Client ID
3. Under **Authorized redirect URIs**, add exactly:
   ```
   http://localhost:8080/api/v1/auth/google/callback
   ```
4. Click **Save**
5. Verify your `.env` matches:
   ```bash
   GOOGLE_REDIRECT_URI=http://localhost:8080/api/v1/auth/google/callback
   ```

**Fix — if running on a remote machine:**

Replace `localhost` with the machine's IP or hostname:

```bash
GOOGLE_REDIRECT_URI=http://192.168.1.100:8080/api/v1/auth/google/callback
```

And add the same URI to Google Cloud Console.

**Fix — OAuth consent screen not configured:**

If you see "This app isn't verified", you need to configure the OAuth consent screen in Google Cloud Console:
1. APIs & Services → OAuth consent screen
2. Set User Type to **External**
3. Add your email as a test user
4. Add the Google Calendar API scope

---

## 9. `flutter analyze` fails

**Symptom:**
```
Analyzing kinfolk...
error • ... • ...
```

**Fix — run analyze and read the output:**

```bash
cd frontend
flutter analyze
```

Common causes:

**Deprecated API (`withOpacity`):**
```
'withOpacity' is deprecated and shouldn't be used.
```
Replace with `withAlpha()`:
```dart
// Before
color.withOpacity(0.5)
// After
color.withAlpha(128)  // 0.5 * 255 = 127.5 ≈ 128
```

**Missing pub dependencies:**
```bash
flutter pub get
flutter analyze
```

**Outdated generated files:**
```bash
flutter pub run build_runner build --delete-conflicting-outputs
flutter analyze
```

**SDK version constraint too tight:**
```yaml
# pubspec.yaml — relax if needed
environment:
  sdk: ^3.7.0
```

---

## 10. Backend won't start — port conflict

**Symptom:**
```
ERROR:    [Errno 98] Address already in use
# or
uvicorn.error: [Errno 98] error while attempting to bind on address ('0.0.0.0', 8080)
```

**Cause:** Something else is already using port 8080 (another Kinfolk instance, a previous run that didn't exit cleanly, or another service).

**Fix — find and kill the process:**

```bash
# Find what's using port 8080
sudo lsof -i :8080
# or
sudo ss -tlnp | grep 8080

# Kill it (replace PID with the actual process ID)
kill -9 PID
```

**Fix — use a different port:**

```bash
# In .env
PORT=8081

# Or pass directly to uvicorn
uvicorn app.main:app --port 8081
```

**Fix — stale uvicorn process:**

```bash
# Kill all uvicorn processes
pkill -f uvicorn

# Then restart
uvicorn app.main:app --port 8080
```

**Fix — systemd service conflict:**

If you have a systemd service for Kinfolk:

```bash
sudo systemctl stop kinfolk
sudo systemctl start kinfolk
```

---

## General Debugging Tips

**Enable debug logging:**

```bash
# In .env
DEBUG=true

# Or pass to uvicorn
uvicorn app.main:app --port 8080 --log-level debug
```

**Check backend logs:**

```bash
# If running as systemd service
journalctl -u kinfolk -f

# If running directly
uvicorn app.main:app --port 8080 2>&1 | tee /tmp/kinfolk.log
```

**Run backend tests:**

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

**Run Flutter tests:**

```bash
cd frontend
flutter test
```

**Check API interactively:**

The FastAPI backend includes Swagger UI at `http://localhost:8080/docs` — use it to test endpoints directly in your browser.
