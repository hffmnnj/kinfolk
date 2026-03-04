# Hardware Setup Guide

This guide covers setting up Kinfolk on a Raspberry Pi 5 with a 1080×1920 portrait display. The same steps apply to any Ubuntu 24.04 ARM64 or x86-64 machine.

---

## Bill of Materials

| Component | Recommended | Notes |
|-----------|-------------|-------|
| Computer | Raspberry Pi 5 (8GB) | 4GB works; 8GB recommended for voice processing |
| Display | Any 1080×1920 portrait monitor | 24" IPS panel gives best readability |
| Microphone | ReSpeaker 4-Mic Array (USB) | Best wake word accuracy; any USB mic works |
| Speaker | USB speaker or 3.5mm | HDMI audio works but has 50–200ms latency |
| Storage | 64GB microSD (A2 rated) | Samsung Pro Endurance or SanDisk Extreme |
| Power supply | Official Raspberry Pi 5 PSU (27W USB-C) | Third-party PSUs cause throttling |
| Case | Optional — 3D-printed or wood frame | Mount display + Pi together |

**Estimated cost:** $200–$450 one-time, no recurring fees.

---

## Raspberry Pi 5 Setup

### 1. Flash Ubuntu 24.04 LTS ARM64

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash the OS:

1. Open Raspberry Pi Imager
2. Choose OS → **Other general-purpose OS → Ubuntu → Ubuntu Server 24.04 LTS (64-bit)**
3. Choose storage → your microSD card
4. Click the gear icon (⚙️) to pre-configure:
   - Set hostname: `kinfolk`
   - Enable SSH
   - Set username/password
   - Configure WiFi (or use Ethernet)
5. Write the image

> **Note:** Use Ubuntu Server, not Desktop. Kinfolk runs its own display stack (Flutter kiosk mode) and doesn't need a full desktop environment.

### 2. First Boot

```bash
# SSH into the Pi
ssh ubuntu@kinfolk.local

# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y \
  git curl wget unzip \
  python3 python3-pip python3-venv \
  build-essential pkg-config
```

### 3. Install System Dependencies

```bash
# Audio (required for voice pipeline)
sudo apt install -y \
  portaudio19-dev libportaudio2 libasound2-dev alsa-utils \
  pipewire pipewire-pulse pipewire-alsa wireplumber \
  gstreamer1.0-plugins-good gstreamer1.0-plugins-base \
  gstreamer1.0-alsa gstreamer1.0-pulseaudio

# Flutter Linux build dependencies
sudo apt install -y \
  libgtk-3-dev clang cmake ninja-build pkg-config \
  liblzma-dev libstdc++-12-dev

# SQLCipher (for encrypted database)
sudo apt install -y libsqlcipher-dev sqlcipher
```

### 4. Install Flutter

```bash
# Download Flutter SDK
cd ~
wget https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.x.x-stable.tar.xz
tar xf flutter_linux_*.tar.xz

# Add to PATH
echo 'export PATH="$HOME/flutter/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify
flutter doctor
```

> **Tip:** Check [flutter.dev/docs/get-started/install/linux](https://docs.flutter.dev/get-started/install/linux) for the latest stable version URL.

---

## Portrait Display Configuration

Kinfolk targets a **1080×1920 portrait** display (a standard 1920×1080 monitor rotated 90°).

### HDMI Configuration

Edit `/boot/firmware/config.txt` (Ubuntu on Pi) or `/boot/config.txt` (Pi OS):

```ini
# Force HDMI output (prevents blank screen on headless boot)
hdmi_force_hotplug=1

# Set resolution to 1080×1920 portrait
# This tells the Pi the display is 1080 wide × 1920 tall
hdmi_group=2
hdmi_mode=87
hdmi_cvt=1080 1920 60 6 0 0 0

# Rotate display 90° clockwise (landscape panel → portrait orientation)
# Use display_rotate=1 for 90° CW, display_rotate=3 for 90° CCW
display_rotate=1
```

Reboot after editing:

```bash
sudo reboot
```

### Verify Display Resolution

After reboot, check the active resolution:

```bash
# Check connected displays
xrandr --query

# Or with Wayland
wlr-randr
```

Expected output should show `1080x1920` as the active mode.

### X11 Rotation (Alternative Method)

If `display_rotate` doesn't work for your display, use X11 rotation instead. Create `/etc/X11/xorg.conf.d/90-monitor.conf`:

```
Section "Monitor"
    Identifier "HDMI-1"
    Option "Rotate" "right"
EndSection
```

---

## Microphone Setup

### USB Microphone (Any)

Plug in the USB microphone and verify detection:

```bash
# List recording devices
arecord -l

# Test recording (5 seconds)
arecord -d 5 -f cd -r 16000 test.wav
aplay test.wav
```

You should hear your voice played back. If not, check the device index:

```bash
# List PulseAudio sources
pactl list sources short

# Set default input (replace N with your device index)
pactl set-default-source alsa_input.usb-N
```

### ReSpeaker 4-Mic Array (Recommended)

The ReSpeaker requires additional drivers:

```bash
# Install driver dependencies
sudo apt install -y dkms raspberrypi-kernel-headers

# Clone and install ReSpeaker drivers
git clone https://github.com/HinTak/seeed-voicecard.git
cd seeed-voicecard
sudo ./install.sh
sudo reboot

# After reboot, verify
arecord -l
# Should show: "seeed-4mic-voicecard"
```

### Verify Audio with PipeWire

Ubuntu 24.04 uses PipeWire by default:

```bash
# Check PipeWire is running
systemctl --user status pipewire pipewire-pulse wireplumber

# Verify PulseAudio compatibility layer
pactl info | grep "Server Name"
# Expected: "Server Name: PulseAudio (on PipeWire X.X.X)"
```

---

## Speaker Setup

### 3.5mm Audio Jack

```bash
# Set 3.5mm as default output
pactl set-default-sink alsa_output.platform-bcm2835_audio.stereo-fallback

# Test
speaker-test -t wav -c 2
```

### USB Speaker

USB speakers are detected automatically. Set as default:

```bash
# List sinks
pactl list sinks short

# Set default (replace N with your device index)
pactl set-default-sink alsa_output.usb-N
```

### HDMI Audio

HDMI audio works out of the box but has 50–200ms latency — acceptable for TTS responses, not ideal for music. For music, use a USB audio adapter.

---

## Kiosk Mode Configuration

Kinfolk is designed to run fullscreen in kiosk mode — no window decorations, no taskbar, no cursor.

### Systemd Service (Recommended)

Create `/etc/systemd/system/kinfolk.service`:

```ini
[Unit]
Description=Kinfolk Smart Display
After=network.target graphical.target

[Service]
Type=simple
User=kinfolk
Environment=DISPLAY=:0
Environment=XDG_RUNTIME_DIR=/run/user/1000
WorkingDirectory=/home/kinfolk/kinfolk
ExecStart=/home/kinfolk/kinfolk/frontend/build/linux/x64/release/bundle/kinfolk
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable kinfolk
sudo systemctl start kinfolk
```

### Auto-Login (Headless X11)

To start the display automatically on boot without a login screen, configure auto-login:

```bash
# Install minimal X11 session manager
sudo apt install -y openbox xorg xinit

# Create auto-start script
cat > ~/.xinitrc << 'EOF'
#!/bin/bash
# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Hide cursor after 1 second of inactivity
unclutter -idle 1 &

# Start Kinfolk
exec /home/kinfolk/kinfolk/frontend/build/linux/x64/release/bundle/kinfolk
EOF

chmod +x ~/.xinitrc
```

Configure auto-login in `/etc/systemd/system/getty@tty1.service.d/autologin.conf`:

```ini
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin kinfolk --noclear %I $TERM
```

Add to `~/.bash_profile`:

```bash
# Start X on login (tty1 only)
if [[ -z $DISPLAY ]] && [[ $(tty) = /dev/tty1 ]]; then
  startx
fi
```

### Flutter Kiosk Mode

The Flutter app is already configured for fullscreen kiosk mode in `frontend/linux/runner/my_application.cc`:

```cpp
// Fullscreen, no window decorations
gtk_window_set_decorated(window, FALSE);
gtk_window_fullscreen(window);
```

No additional configuration needed.

---

## Power Supply

**Always use the official Raspberry Pi 5 PSU (27W USB-C PD).** Third-party supplies that don't support USB-C PD negotiation will cause:

- CPU throttling (performance drops)
- Undervoltage warnings in `dmesg`
- Random reboots under load

Check for undervoltage:

```bash
# Look for undervoltage warnings
dmesg | grep -i "voltage\|throttl"

# Or check vcgencmd
vcgencmd get_throttled
# 0x0 = no throttling (good)
# 0x50005 = throttled (bad — check PSU)
```

---

## Hardware Verification Checklist

Before running Kinfolk, verify each component:

- [ ] Display shows output at 1080×1920 portrait
- [ ] `arecord -l` shows your microphone
- [ ] `arecord -d 3 -f cd test.wav && aplay test.wav` records and plays back
- [ ] `pactl info` shows PipeWire running
- [ ] `speaker-test -t wav -c 2` produces audio
- [ ] `vcgencmd get_throttled` returns `0x0`
- [ ] `flutter doctor` shows no critical issues
- [ ] `curl http://localhost:8080/health` returns `{"status":"healthy"}`

---

## Next Steps

- Configure environment variables: [`docs/configuration.md`](configuration.md)
- Understand the architecture: [`docs/architecture.md`](architecture.md)
- Troubleshoot issues: [`docs/troubleshooting.md`](troubleshooting.md)
