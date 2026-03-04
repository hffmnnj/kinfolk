# Rhasspy / Wyoming-OpenWakeWord Docker Setup

This directory contains Docker configuration for the wake word detection service.

## Recommended: Wyoming-OpenWakeWord

For the alpha release, Kinfolk uses `rhasspy/wyoming-openwakeword` instead of the full Rhasspy 2.5 container. This is lighter weight and focused on wake word detection.

### Quick Start

```bash
# Pull the image (multi-arch: supports ARM64 and x86-64)
docker pull rhasspy/wyoming-openwakeword

# Run with default models
docker run -d \
  --name kinfolk-wakeword \
  -p 10400:10400 \
  --device /dev/snd:/dev/snd \
  rhasspy/wyoming-openwakeword \
  --preload-model "ok_nabu"

# Run with custom wake word models
docker run -d \
  --name kinfolk-wakeword \
  -p 10400:10400 \
  --device /dev/snd:/dev/snd \
  -v ./models:/custom \
  rhasspy/wyoming-openwakeword \
  --custom-model-dir /custom
```

### Custom Wake Word Training

To train "Hey Kin" and "Kinfolk" wake words:

1. Use the openWakeWord training pipeline (requires Python 3.10+ and optionally a GPU)
2. Generate synthetic speech samples for the target phrases
3. Train a small model on top of the frozen feature extractor
4. Place the resulting `.tflite` model files in the `models/` directory

See: https://github.com/dscripka/openWakeWord#training-new-models

### Audio Access in Docker

The container needs access to the host audio system:

```bash
# ALSA direct access
--device /dev/snd:/dev/snd

# PulseAudio socket (for PipeWire compatibility)
-v /run/user/1000/pulse:/run/user/1000/pulse
-e PULSE_SERVER=unix:/run/user/1000/pulse/native
```

### Docker Compose Integration

This service is included in the project's `docker-compose.yml`:

```yaml
services:
  wakeword:
    image: rhasspy/wyoming-openwakeword
    ports:
      - "10400:10400"
    devices:
      - /dev/snd:/dev/snd
    volumes:
      - ./docker/rhasspy/models:/custom
      - /run/user/1000/pulse:/run/user/1000/pulse
    environment:
      - PULSE_SERVER=unix:/run/user/1000/pulse/native
    command: --custom-model-dir /custom
    restart: unless-stopped
```

## Why Not Full Rhasspy 2.5?

The full Rhasspy 2.5 Docker image (`rhasspy/rhasspy`) includes wake word, STT, TTS, NLU, and dialogue management. For Kinfolk:

- **Wake word:** Handled by Wyoming-OpenWakeWord (lighter)
- **STT:** Handled by Python backend (Whisper API / Vosk)
- **TTS:** Handled by Python backend (NanoTTS / gTTS)
- **NLU:** Handled by Python backend (Rhasspy NLU library or rule-based)

Using the full Rhasspy container would duplicate functionality already in the backend.

## Why Not System Install?

Rhasspy 2.5 system packages target Python 3.7-3.9. Ubuntu 24.04 ships Python 3.12, causing dependency conflicts. Docker isolates these version requirements.

---

*See also: `docs/compatibility.md` for full compatibility notes.*
