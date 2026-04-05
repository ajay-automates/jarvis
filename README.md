# 🤖 J.A.R.V.I.S. — Just A Rather Very Intelligent System

A complete voice-controlled Mac assistant powered by Claude AI. Clap your hands or say **"Hey Jarvis"** to activate, then speak your command.

---

## ⚡ Quick Start

```bash
# 1. Set your API key
export ANTHROPIC_API_KEY="your-key-here"

# 2. Install dependencies
bash setup.sh

# 3. Run Jarvis
python3 jarvis.py
```

---

## 🎛️ Modes

| Mode | Command | Description |
|------|---------|-------------|
| **Full Voice** | `python3 jarvis.py` | Clap + wake word + voice commands |
| **Text Mode** | `python3 jarvis.py --text` | Type commands (great for testing) |
| **Debug** | `python3 jarvis.py --debug` | Verbose output for troubleshooting |

---

## 🎤 Wake Triggers

### 👏 Clap Detection
Clap your hands sharply. Adjust sensitivity:
```bash
python3 jarvis.py --threshold 0.4   # More sensitive (noisy rooms)
python3 jarvis.py --threshold 0.8   # Less sensitive (quiet rooms)
```

### 🗣️ Wake Word
Say **"Hey Jarvis"** or just **"Jarvis"**.

---

## 💬 Example Commands

### Apps & Browser
- "Open Safari and go to GitHub"
- "Launch VS Code"
- "Close Finder"
- "Switch to Slack"
- "Open my Downloads folder"

### Spotify & Media
- "Play some music"
- "Pause the music"
- "Next track"
- "What song is playing?"
- "Set volume to 50 percent"
- "Turn on shuffle"

### Calendar & Reminders
- "What's on my calendar today?"
- "Do I have any meetings this afternoon?"
- "Create a reminder to call mom at 5pm"

### Email
- "Read my latest emails"
- "Do I have any unread messages?"
- "Compose an email to John about the meeting"

### System Controls
- "Turn on dark mode"
- "Set brightness to maximum"
- "Mute the volume"
- "Lock the screen"
- "What's my battery level?"
- "Take a screenshot"
- "Turn off Wi-Fi"

### Fun
- "Tell me a joke"
- "What time is it?"
- "Good morning, Jarvis"

---

## 🗣️ Change Voice

List available voices:
```bash
say -v '?'
```

Popular choices:
```bash
python3 jarvis.py --voice "Daniel"    # British (default, very Jarvis)
python3 jarvis.py --voice "Alex"      # American
python3 jarvis.py --voice "Samantha"  # American female
python3 jarvis.py --voice "Moira"     # Irish
python3 jarvis.py --voice "Rishi"     # Indian English
```

---

## 🔧 Configuration

Edit the **CONFIGURATION** section at the top of `jarvis.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_VOICE` | `"Daniel"` | macOS TTS voice |
| `JARVIS_RATE` | `180` | Speech speed (words/min) |
| `CLAP_THRESHOLD` | `0.6` | Clap sensitivity (0.0–1.0) |
| `WAKE_WORD` | `"jarvis"` | Wake word trigger |
| `LISTEN_TIMEOUT` | `7` | Seconds to wait for command |

---

## 🔒 Privacy

- All voice processing uses Google Speech Recognition (free tier)
- Commands are sent to Claude API for interpretation
- No audio is stored — everything is processed in real-time
- All Mac control happens locally via AppleScript

---

## 🐛 Troubleshooting

**"Microphone not working"**
→ System Preferences → Privacy & Security → Microphone → Allow Terminal/iTerm

**"pyaudio install fails"**
```bash
brew install portaudio
pip3 install pyaudio
```

**"Clap detection too sensitive / not sensitive enough"**
→ Use `--threshold` flag or `--debug` to see amplitude values

**"Speech not recognized"**
→ Speak clearly, reduce background noise
→ Google Speech Recognition needs internet

**"AppleScript permission denied"**
→ System Preferences → Privacy & Security → Automation → Allow Terminal
→ Also check Accessibility permissions

---

## 📁 Project Structure

```
jarvis/
├── jarvis.py      # Main application (all-in-one)
├── setup.sh       # Installation script
└── README.md      # This file
```

---

## 🚀 Future Enhancements

- [ ] Picovoice Porcupine for offline wake word (no internet needed)
- [ ] ElevenLabs integration for realistic voice
- [ ] Menu bar app with status indicator
- [ ] Shortcut key trigger (e.g., double-tap Fn)
- [ ] Local Whisper for offline speech recognition
- [ ] HomeKit integration for smart home control
- [ ] Multi-monitor window management
- [ ] Custom routines ("Good morning" → open apps + read calendar + weather)

---

*"At your service, sir."* 🫡
