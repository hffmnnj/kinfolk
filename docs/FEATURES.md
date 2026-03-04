# Kinfolk - Complete Feature Specification

**Last Updated:** March 2026  
**Version:** 0.1.0-alpha

---

## Table of Contents

1. [Core Dashboard](#core-dashboard)
2. [Voice Assistant](#voice-assistant)
3. [Calendar & Tasks](#calendar--tasks)
4. [Media & Entertainment](#media--entertainment)
5. [Communication](#communication)
6. [Smart Home](#smart-home)
7. [Utilities](#utilities)
8. [User Profiles](#user-profiles)
9. [Settings & Configuration](#settings--configuration)
10. [Developer Features](#developer-features)

---

## Core Dashboard

### Always-On Home Screen

**Display Elements:**

**Clock Widget** (Top Center)
- Current time (large, readable from distance)
- Current date
- Day of week
- Format: 12h/24h toggle
- Timezone support
- Smooth second hand animation (optional)

**Weather Widget** (Top Right)
- Current conditions (icon + temperature)
- "Feels like" temperature
- Humidity, wind speed
- 5-day forecast (swipeable)
- Weather alerts (severe weather)
- Location-based (auto-detect or manual)
- API: OpenWeatherMap or Weather.gov

**Calendar Summary** (Center)
- Today's events (next 3)
- Tomorrow preview
- Color-coded by person
- Tap to expand full calendar
- Shows event title, time, location
- Countdown to next event

**To-Do List Preview** (Bottom Left)
- Next 3 incomplete tasks
- Checkboxes (tap to complete)
- Add button (+ icon)
- Shows who assigned/created
- Priority indicators (high = red dot)

**Quick Actions Bar** (Bottom)
- Music controls
- Timer/stopwatch
- Smart home shortcuts
- Message center
- Settings

---

### Layout Modes

**Default Mode:** Dashboard (shown above)

**Focus Mode:**
- Clock + single widget (fullscreen)
- Minimal distractions
- Good for bedrooms

**Photo Frame Mode:**
- Slideshow of family photos
- Metadata overlay (date, location)
- Transition effects (fade, slide)
- Duration: 10s-60s per photo

**Screensaver Mode:**
- Activates after 30min idle
- Clock + minimal info
- Dim brightness
- Touch/voice to wake

---

## Voice Assistant

### Wake Word Detection

**Primary Wake Word:** "Hey Kin" or "Kinfolk"

**Customizable:**
- User can set custom wake word
- Multi-language support
- Sensitivity adjustment (reduce false positives)

**Visual Feedback:**
- LED ring animation (if hardware supports)
- On-screen pulse animation
- Voice waveform display

**Privacy:**
- Wake word detection 100% local (Rhasspy/Porcupine)
- No audio sent to cloud until wake word detected
- Optional: Disable listening (hardware mute switch)

---

### Voice Commands

**Calendar & Events**
```
"What's on my calendar today?"
"When is my next meeting?"
"Add event: Dentist appointment tomorrow at 2pm"
"Cancel my 3pm meeting"
"Show me this week's calendar"
```

**To-Do Lists**
```
"Add milk to the shopping list"
"What's on my to-do list?"
"Mark 'call doctor' as done"
"Create a new list called 'Home Projects'"
"Remove bread from shopping list"
```

**Weather**
```
"What's the weather today?"
"Will it rain this weekend?"
"What's the temperature?"
"Weather forecast for next week"
```

**Music**
```
"Play some jazz music"
"Play [song name] by [artist]"
"Skip this song"
"Volume up/down"
"Pause music"
"What song is this?"
```

**Timers & Alarms**
```
"Set a timer for 10 minutes"
"Set an alarm for 7am"
"How much time is left on my timer?"
"Cancel all timers"
"Snooze alarm"
```

**Photos**
```
"Show photos from last Christmas"
"Show me photos of [person name]"
"Start photo slideshow"
"Show recent photos"
```

**Smart Home**
```
"Turn off the living room lights"
"Set bedroom temperature to 68 degrees"
"Lock the front door"
"Show me the front door camera"
"Turn on movie mode"
```

**Communication**
```
"Leave a message for [family member]"
"Read my messages"
"Call [contact name]"
"Show family chat"
```

**Information**
```
"What's the news?"
"How do I convert cups to grams?"
"Tell me a joke"
"What's the traffic like?"
"Define [word]"
```

**System**
```
"Go to settings"
"Switch to [person name]'s profile"
"Show calendar"
"Take a screenshot"
"Goodnight" (activates night mode)
"Good morning" (morning briefing)
```

---

### Natural Language Processing

**Conversational AI:**
- Follow-up questions without wake word
- Context awareness (30s window)
- Example:
  ```
  User: "What's the weather?"
  Kin: "It's 75 and sunny."
  User: "Will it rain later?"
  Kin: "No rain in the forecast today."
  ```

**Multi-Intent:**
```
"Add eggs to shopping list and set a timer for 5 minutes"
→ Executes both commands
```

**Corrections:**
```
User: "Set alarm for 7pm... wait, make that 8pm"
Kin: "Okay, setting alarm for 8pm instead."
```

---

### Text-to-Speech (TTS)

**Voice Options:**
- Default: Warm, neutral voice
- Alternate voices available
- Speed adjustment (0.8x - 1.5x)
- Volume independent of media

**Response Types:**
- **Confirmation:** Short, quick ("Done", "Okay")
- **Information:** Detailed responses
- **Error:** Friendly error handling ("Sorry, I didn't understand that")

---

## Calendar & Tasks

### Shared Family Calendar

**Calendar Sources:**
- Google Calendar (OAuth)
- CalDAV (Nextcloud, iCloud, etc.)
- Local calendar (SQLite)
- Multiple calendars per person

**Views:**
- **Day:** Today's events (default)
- **Week:** 7-day overview
- **Month:** Full month grid
- **Agenda:** List of upcoming events

**Event Details:**
- Title, time, location
- Attendees
- Notes/description
- Reminders (15min, 1hr, 1day before)
- Color coding by person/category

**Event Management:**
- Create events (voice or touch)
- Edit events
- Delete events
- Set recurring events
- Invite family members
- RSVP to events

**Integration:**
- Sync with phone calendars
- Email invites (via SMTP)
- Notification center alerts

---

### To-Do Lists

**List Types:**
- Shopping list
- Chores
- Projects
- Personal tasks
- Custom lists

**Task Properties:**
- Title
- Due date (optional)
- Assigned to (person)
- Priority (low, medium, high)
- Notes
- Subtasks
- Completed status

**List Sharing:**
- Family-wide lists (shopping, chores)
- Personal lists
- Permissions (view, edit)

**Smart Features:**
- Recurring tasks
- Location-based reminders
- Voice add/complete
- Sort by: priority, due date, person
- Archive completed tasks

---

### Notifications & Reminders

**Notification Types:**
- Calendar events (15min before)
- Task due dates
- Weather alerts
- Family messages
- Smart home alerts
- System updates

**Notification Display:**
- Toast notifications (corner)
- Notification center (swipe down)
- Voice announcements (optional)
- LED indicator (if hardware supports)

**Do Not Disturb:**
- Scheduled quiet hours (10pm-7am default)
- Critical alerts only
- Visual notifications only (no voice)
- Per-person DND settings

---

## Media & Entertainment

### Music Player

**Music Sources:**
- Spotify (OAuth)
- Local music library (MP3, FLAC, OGG)
- Web radio streams
- YouTube Music (unofficial API)
- Subsonic/Navidrome servers

**Playback Controls:**
- Play/pause
- Skip forward/back
- Volume control
- Shuffle
- Repeat
- Queue management

**Display:**
- Album art (large)
- Song title, artist, album
- Progress bar
- Lyrics (via Genius API)
- Visualizer (waveform, spectrum)

**Voice Control:**
- "Play [artist/song/playlist]"
- "Skip song"
- "Add to favorites"
- "Volume 50 percent"

**Multi-Room Audio:** (Future)
- Cast to other speakers
- Synchronize playback
- Group speakers

---

### Photo Frame

**Photo Sources:**
- Google Photos (OAuth)
- Local folder (USB drive, NAS)
- Nextcloud Photos
- Amazon Photos
- Manual upload

**Slideshow:**
- Random or chronological
- Transition effects (fade, slide, zoom)
- Duration per photo (10s-60s)
- Face detection (show photos with family)
- Date range filter

**Metadata Display:**
- Date taken
- Location (if GPS data)
- People tagged
- Album name

**Smart Features:**
- "On this day" (photos from same date)
- Face recognition (group by person)
- Favorites collection
- Exclude photos (mark as private)

---

### Video Playback

**Supported Sources:**
- YouTube (via API)
- Local video files (MP4, MKV, AVI)
- Jellyfin/Plex integration (future)

**Use Cases:**
- Cooking videos (recipe walkthroughs)
- Kids content (YouTube Kids)
- Family videos
- News clips

**Controls:**
- Play/pause
- Skip forward/back (10s)
- Volume
- Fullscreen
- Subtitles

---

### News & Information

**News Sources:**
- RSS feeds (customizable)
- News APIs (NewsAPI, NYTimes)
- Local news
- Weather alerts

**Display:**
- Scrolling news ticker (bottom)
- News card (tap to expand)
- Categories (local, tech, sports, etc.)

**Voice Briefing:**
```
"What's the news?"
→ Reads top 3 headlines
```

---

## Communication

### Family Message Board

**Message Types:**
- Text notes
- Voice notes (recorded)
- Quick messages (pre-set: "Running late", "Love you")
- Shared photos

**Features:**
- Leave message for specific person
- Family-wide broadcasts
- Reply to messages
- Delete messages
- Mark as read

**Display:**
- Message icon badge (unread count)
- Notification on new message
- Message history (last 30 days)

**Voice:**
```
"Leave a message for Sarah: Don't forget your lunch"
"Read my messages"
"Reply: Thanks, I'll grab it"
```

---

### Video Calls

**Supported Platforms:**
- Zoom (via web SDK)
- Google Meet (web)
- Jitsi Meet (self-hosted)
- Custom WebRTC

**Features:**
- One-tap join (from calendar invite)
- Voice command to start call
- Camera on/off
- Mute/unmute
- Screen share (view only)

**Use Cases:**
- Grandparent video calls
- Family check-ins
- Remote work meetings

---

### Intercom Mode

**Broadcast Messages:**
- Send voice message to other Kinfolk displays
- Room-to-room communication
- "Come to dinner" announcements

**Drop-In:** (Optional, privacy concerns)
- Two-way audio with other Kinfolk displays
- Requires explicit permission
- Visual indicator when active

---

## Smart Home

### Home Assistant Integration

**Device Control:**
- Lights (on/off, brightness, color)
- Thermostats (temp, mode)
- Locks (lock/unlock)
- Cameras (live view)
- Switches (outlets, appliances)
- Sensors (door, motion, temperature)
- Garage doors
- Window blinds

**Scenes:**
- "Movie mode" (dim lights, close blinds)
- "Goodnight" (lock doors, turn off lights, arm security)
- "Good morning" (open blinds, turn on lights, start coffee)
- "Away mode" (security settings)

**Automations:**
- Time-based (turn on lights at sunset)
- Sensor-based (motion → lights)
- Voice-triggered
- Location-based (arrive/leave home)

**Dashboard Widget:**
- Quick controls for common devices
- Room-by-room view
- Status indicators (locked, on/off)
- Energy usage (if supported)

---

### Camera Feeds

**Display Modes:**
- Single camera (fullscreen)
- Multi-camera (grid view)
- Picture-in-picture
- Rotate through cameras

**Cameras:**
- Front door
- Backyard
- Baby monitor
- Pet camera
- Security cameras

**Features:**
- Live stream
- Recorded clips (if supported)
- Motion alerts
- Two-way audio (if camera supports)

---

## Utilities

### Timers & Alarms

**Timers:**
- Multiple simultaneous timers
- Named timers ("laundry", "cookies")
- Voice control to set/cancel
- Visual countdown
- Audio + visual alert

**Alarms:**
- Daily alarms
- One-time alarms
- Recurring (weekdays, weekends)
- Custom labels
- Snooze functionality
- Gradual volume increase

**Stopwatch:**
- Start/stop/reset
- Lap times
- Display milliseconds

---

### Recipes & Cooking

**Recipe Display:**
- Step-by-step instructions
- Ingredient list
- Timer integration
- Voice navigation ("next step", "repeat step")
- Scaling (2x, 0.5x recipe)

**Sources:**
- Recipe websites (via import)
- Manual entry
- Family recipes (saved locally)

**Features:**
- Hands-free cooking (voice only)
- Keep screen on while cooking
- Measurement conversions
- Shopping list integration (add ingredients)

---

### Unit Conversions

**Supported Conversions:**
- Cooking (cups ↔ grams, tsp ↔ ml)
- Temperature (F ↔ C)
- Distance (miles ↔ km)
- Weight (lbs ↔ kg)
- Time zones
- Currency (via API)

**Voice:**
```
"How many grams in 2 cups of flour?"
"Convert 72 Fahrenheit to Celsius"
```

---

### Calculator

**Basic Math:**
- Addition, subtraction, multiplication, division
- Percentages
- Square roots
- Memory functions

**Voice Calculator:**
```
"What's 15 percent of 80?"
"Divide 144 by 12"
```

---

## User Profiles

### Multi-User Support

**Profile Types:**
- **Admin:** Full control
- **Adult:** Standard features
- **Child:** Restricted content & controls
- **Guest:** Limited access

**User Switching:**
- Face recognition (via camera)
- Voice identification
- Manual selection (tap profile icon)
- Auto-switch based on calendar/schedule

---

### Personalization

**Per-User Settings:**
- Calendar sources
- Music preferences
- News interests
- Voice assistant voice
- Notification preferences
- Privacy settings
- Theme customization

**Child Profile Features:**
- Content filters (YouTube Kids, safe websites)
- Screen time limits
- Approved apps only
- Parental controls
- Educational content priority

---

### Face Recognition (Optional)

**Features:**
- Auto-detect user
- Personalized greeting
- Switch calendar view
- Show relevant notifications
- Privacy-first (all local processing)

**Setup:**
- Capture 10-15 face samples
- Train model locally (no cloud)
- Delete/retrain anytime

**Privacy:**
- Can be disabled
- Camera shutter option
- No face data stored in cloud
- Delete all face data option

---

## Settings & Configuration

### Display Settings

- Brightness (auto or manual)
- Night mode (scheduled)
- Screen timeout
- Orientation lock
- Touch calibration
- Color temperature

### Audio Settings

- Microphone sensitivity
- Speaker volume (voice, media, alarms)
- Wake word settings
- TTS voice selection
- Audio output device

### Network Settings

- WiFi configuration
- Ethernet settings
- Static IP
- VPN support
- Firewall rules

### Privacy Settings

- Voice recording retention
- Camera on/off
- Face recognition toggle
- Data sharing preferences
- Activity logs
- Reset all data

### System Settings

- Software updates
- Backup & restore
- Factory reset
- Developer mode
- Diagnostic logs
- About/version info

---

## Developer Features

### Plugin System

**Plugin Architecture:**
- Hot-reload plugins
- Custom widgets
- Custom voice commands
- API extensions
- Theme plugins

**Plugin Repository:**
- Community marketplace
- Install via UI
- Auto-updates
- Dependency management

### API

**REST API:**
- GET/POST endpoints for all features
- Authentication (API keys)
- Webhooks
- Real-time websockets

**Example Endpoints:**
```
POST /api/calendar/events
GET /api/weather
POST /api/voice/command
GET /api/users/{id}/preferences
```

### Customization

- Custom CSS themes
- Widget layouts (drag & drop)
- Custom voice commands
- Automation scripts
- Integration adapters

---

## Future Features (Roadmap)

**Phase 2 (Q3 2026):**
- [ ] Meal planning integration
- [ ] Fitness tracking display
- [ ] Handwriting recognition
- [ ] Language learning flashcards
- [ ] Pet care reminders

**Phase 3 (Q4 2026):**
- [ ] Multi-display synchronization
- [ ] Mobile companion app
- [ ] Video doorbell integration
- [ ] AR try-on (shopping)
- [ ] Family journal/diary

**Community Requests:**
- [ ] Recipe suggestions based on pantry
- [ ] Chore rotation system
- [ ] Allowance tracker (kids)
- [ ] Package tracking
- [ ] Plant care reminders

---

## Feature Priority Matrix

**MVP (Must Have):**
- Dashboard (clock, weather, calendar)
- Voice commands (basic)
- Calendar & tasks
- Music playback
- Settings

**Phase 1 (Nice to Have):**
- Photo frame mode
- Smart home control
- Video calls
- News display
- Multi-user profiles

**Phase 2 (Future):**
- Advanced AI features
- Multi-display sync
- Mobile app
- Plugin marketplace
- Advanced automations

---

**Version History:**
- v0.1.0 - Initial feature spec (March 2026)

