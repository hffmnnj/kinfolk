# Kinfolk: Dependency Compatibility Notes

This document covers compatibility findings for Kinfolk's key external dependencies on the target platform (Raspberry Pi 5, Ubuntu 24.04 LTS ARM64).

---

## Voice / Wake Word Detection

### Recommended: openWakeWord

Kinfolk uses [openWakeWord](https://github.com/dscripka/openWakeWord) for local wake word detection. This is a lightweight, open-source wake word engine that runs entirely on-device.

**Why openWakeWord:**
- Fully open-source (Apache 2.0) — no license restrictions for custom wake words
- Runs on Raspberry Pi 5 with minimal CPU usage
- Custom wake words ("Hey Kin", "Kinfolk") can be trained without cloud services
- Available as a Python package (`pip install openwakeword`) or Docker container (`rhasspy/wyoming-openwakeword`)

**System requirements:**
```bash
# Python package
pip install openwakeword>=0.6.0

# Or via Docker (production deployment)
docker run -p 10400:10400 rhasspy/wyoming-openwakeword \
  --custom-model-dir /path/to/models
```

**Alternative:** If openWakeWord doesn't meet accuracy requirements, Picovoice Porcupine can be used with built-in wake words (free tier) or custom wake words (requires Enterprise license).

### Audio Capture

Audio is captured by the Python backend using the `sounddevice` library (PortAudio bindings). Flutter does not access the microphone directly.

**Required system packages:**
```bash
sudo apt install -y portaudio19-dev libportaudio2 libasound2-dev alsa-utils
```

**Microphone setup:**
- USB microphones are recommended for best compatibility
- Plug in the USB mic and verify detection: `arecord -l`
- ReSpeaker mic arrays are supported but require additional driver installation

---

## Music Playback

### Mopidy with Local Files

Kinfolk uses [Mopidy](https://mopidy.com/) as its music server, controlled via JSON-RPC over HTTP.

**Supported formats:** MP3, FLAC, OGG, WAV, M4A

**Setup:**
```bash
# Install Mopidy and plugins
sudo apt install -y mopidy gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly

# Or via pip
pip install Mopidy Mopidy-Local
```

**Configuration** (`~/.config/mopidy/mopidy.conf`):
```ini
[local]
media_dir = /home/kinfolk/Music

[http]
hostname = 0.0.0.0
port = 6680
```

Place your music files in the configured media directory. Mopidy will scan them on startup.

### Spotify Integration — Not Available in Alpha

**Status: Deferred**

Spotify integration via `mopidy-spotify` is not included in the alpha release due to:

1. **Spotify API restrictions (March 2026):** Spotify now requires Premium accounts for developers and limits Development Mode to 5 authorized users. This makes it impractical for an open-source project.
2. **mopidy-spotify instability:** The v5.0 release has unresolved playback issues and requires building Rust dependencies from source.
3. **Build complexity:** The required GStreamer Spotify plugin needs a Rust/Cargo toolchain, which adds significant setup complexity on ARM64.

**Future plans:** Spotify support will be revisited when mopidy-spotify stabilizes and Spotify's API policies become clearer for open-source projects.

**Workaround:** Users who want Spotify can run a separate [librespot](https://github.com/librespot-org/librespot) instance as a Spotify Connect receiver alongside Kinfolk.

---

## Audio System (PipeWire / PulseAudio)

### Ubuntu 24.04 Default: PipeWire

Ubuntu 24.04 uses PipeWire as the default audio server with full PulseAudio compatibility. No special configuration is needed for most setups.

**Verify PipeWire is running:**
```bash
# Check service status
systemctl --user status pipewire pipewire-pulse wireplumber

# Verify PulseAudio compatibility layer
pactl info | grep "Server Name"
# Expected output: "Server Name: PulseAudio (on PipeWire X.X.X)"
```

**Required system packages:**
```bash
# Usually pre-installed on Ubuntu 24.04
sudo apt install -y \
  pipewire pipewire-pulse pipewire-alsa wireplumber \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-base \
  gstreamer1.0-alsa gstreamer1.0-pulseaudio
```

### Raspberry Pi 5 Audio Setup

**HDMI audio (default):**
- Works out of the box for the built-in display
- May have 50-200ms latency — acceptable for TTS responses

**USB microphone (recommended for voice input):**
```bash
# Verify USB mic is detected
arecord -l

# Test recording
arecord -d 5 -f cd test.wav
aplay test.wav
```

**3.5mm audio jack:**
```bash
# Set as default output if needed
pactl set-default-sink alsa_output.platform-bcm2835_audio.stereo-fallback
```

### Known Limitations

| Issue | Impact | Workaround |
|-------|--------|------------|
| HDMI audio latency (50-200ms) | Low — acceptable for TTS | Use USB audio adapter for lower latency |
| USB mic hot-plug issues | Low — rare | Restart PipeWire: `systemctl --user restart pipewire` |
| Bluetooth audio latency | Medium | Not recommended for voice assistant use |
| Docker audio access | Medium | Mount PulseAudio socket into containers (see Docker setup docs) |

---

## Docker Audio Access

Services running in Docker containers (wake word engine, Mopidy) need access to the host audio system.

**Docker run flags for audio:**
```bash
docker run ... \
  --device /dev/snd:/dev/snd \
  -v /run/user/$(id -u)/pulse:/run/user/1000/pulse \
  -e PULSE_SERVER=unix:/run/user/1000/pulse/native \
  ...
```

**Docker Compose example:**
```yaml
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

---

## Compatibility Matrix

| Component | Status | Platform | Notes |
|-----------|--------|----------|-------|
| openWakeWord | Supported | RPi5 ARM64, x86-64 | Custom wake words, Apache 2.0 |
| Mopidy (local files) | Supported | RPi5 ARM64, x86-64 | MP3, FLAC, OGG, WAV |
| mopidy-spotify | Not supported (alpha) | — | Deferred due to API restrictions |
| PipeWire audio | Supported | Ubuntu 24.04 | Default audio server |
| Python sounddevice | Supported | RPi5 ARM64, x86-64 | Via PortAudio |
| Flutter audioplayers | Supported | Linux Desktop | Via GStreamer |
| USB microphones | Supported | RPi5 | Recommended for voice input |
| ReSpeaker mic array | Supported | RPi5 | Requires driver installation |
| Bluetooth audio | Limited | RPi5 | High latency, not recommended |

---

## Hardware Verification Checklist

Before deploying Kinfolk on new hardware, verify:

- [ ] PipeWire is running (`pactl info`)
- [ ] Microphone is detected (`arecord -l`)
- [ ] Audio output works (`aplay /usr/share/sounds/alsa/Front_Center.wav`)
- [ ] Docker can access audio devices
- [ ] Mopidy plays a test audio file
- [ ] Wake word detection responds to "Hey Kin"

---

*Last updated: 2026-03-04*
