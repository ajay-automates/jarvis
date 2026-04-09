#!/usr/bin/env python3
"""
🤖 J.A.R.V.I.S. — Just A Rather Very Intelligent System
A voice-controlled Mac assistant powered by Claude AI.

Wake triggers: Clap detection + "Hey Jarvis" wake word
Controls: Apps, Browser, Spotify, Calendar, Email, System Settings
Voice: macOS built-in TTS

Requirements:
    pip install anthropic sounddevice numpy speechrecognition pyaudio
"""

import os
import sys
import json
import time
import struct
import subprocess
import threading
import queue
import wave
import tempfile
import math
import re
from datetime import datetime

# --- Dependency check ---
def check_dependencies():
    missing = []
    try:
        import sounddevice
    except ImportError:
        missing.append("sounddevice")
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    try:
        import speech_recognition
    except ImportError:
        missing.append("SpeechRecognition")
    try:
        import anthropic
    except ImportError:
        missing.append("anthropic")

    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print(f"   Run: pip install {' '.join(missing)}")
        sys.exit(1)

check_dependencies()

import sounddevice as sd
import numpy as np
import speech_recognition as sr
import anthropic

# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
JARVIS_VOICE = "Daniel"           # macOS voice (Daniel = British, try 'Alex', 'Samantha', etc.)
JARVIS_RATE = 180                 # Speech rate (words per minute)
SAMPLE_RATE = 16000               # Audio sample rate
CLAP_THRESHOLD = 0.6              # Amplitude threshold for clap detection (0.0-1.0)
CLAP_COOLDOWN = 1.0               # Seconds between clap triggers
WAKE_WORD = "jarvis"              # Wake word to listen for
LISTEN_TIMEOUT = 7                # Seconds to wait for a command after activation
COMMAND_TIMEOUT = 10              # Max seconds for a single command recording
DEBUG = os.environ.get("JARVIS_DEBUG", "false").lower() == "true"

# ═══════════════════════════════════════════════════════════
# JARVIS BRAIN — Claude AI Integration
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are J.A.R.V.I.S., an AI assistant that controls a Mac computer via voice commands.
You are witty, efficient, and slightly British in demeanor — like the original Jarvis.

When the user gives a command, you MUST respond with a JSON object containing:
{
    "speech": "What you say back to the user (keep it brief and Jarvis-like)",
    "actions": [
        {
            "type": "applescript" | "shell" | "none",
            "code": "the AppleScript or shell command to execute",
            "description": "what this action does"
        }
    ]
}

CAPABILITIES (use AppleScript via osascript unless shell is simpler):

1. **Apps & Browser**:
   - Open/close/switch apps: `tell application "AppName" to activate`
   - Open URLs: `open location "https://..."`
   - Safari/Chrome navigation, tab management
   - Finder operations (open folders, move files)
   - System Preferences panes

2. **Spotify & Media**:
   - Play/pause: `tell application "Spotify" to playpause`
   - Next/previous track: `tell application "Spotify" to next track` / `previous track`
   - Play specific playlist/artist: `tell application "Spotify" to play track "spotify:playlist:..."`
   - Get current track: `tell application "Spotify" to return name of current track & " by " & artist of current track`
   - Volume control: `set sound volume to 50` (0-100)
   - Set shuffle: `tell application "Spotify" to set shuffling to true`

3. **Calendar & Reminders**:
   - Read today's events using Calendar app AppleScript
   - Create reminders, events

4. **Email (Mail.app)**:
   - Read recent emails using Mail app AppleScript
   - Compose new email

5. **System Controls**:
   - Brightness: shell command `brightness 0.8` (if installed) or use AppleScript
   - Volume: `set volume output volume 50`
   - Mute/unmute: `set volume output muted true/false`
   - Dark/Light mode: `tell application "System Events" to tell appearance preferences to set dark mode to true`
   - Do Not Disturb, screenshots, sleep, lock screen
   - Wi-Fi on/off: `networksetup -setairportpower en0 on/off`
   - Battery info: shell `pmset -g batt`
   - Screen lock: shell `pmset displaysleepnow`

6. **Window Management**:
   - Resize/move windows via System Events
   - Minimize/maximize, full screen toggle

7. **Clipboard & Text**:
   - Read clipboard: `the clipboard`
   - Set clipboard: `set the clipboard to "text"`

8. **Notifications**:
   - `display notification "message" with title "Jarvis"`

RULES:
- Always respond with valid JSON only — no markdown, no extra text.
- Keep "speech" responses concise (1-2 sentences max) and in Jarvis character.
- If the command is unclear, ask for clarification in the "speech" field and set actions to [{"type": "none", "code": "", "description": "Waiting for clarification"}].
- For multi-step commands, include multiple actions in the array.
- If you need to read output (like calendar events or emails), the action's result will be passed back to you.
- Current date/time: {datetime}
"""


class JarvisBrain:
    """Claude-powered command interpreter."""

    def __init__(self):
        if not ANTHROPIC_API_KEY:
            print("❌ ANTHROPIC_API_KEY not set!")
            print("   Run: export ANTHROPIC_API_KEY='your-key-here'")
            sys.exit(1)
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.conversation_history = []

    def think(self, command: str, context: str = "") -> dict:
        """Send a command to Claude and get structured response."""
        prompt = command
        if context:
            prompt = f"{command}\n\n[Context from previous action result: {context}]"

        self.conversation_history.append({"role": "user", "content": prompt})

        # Keep conversation short to stay fast
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-10:]

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=SYSTEM_PROMPT.replace("{datetime}", datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")),
                messages=self.conversation_history,
            )
            reply = response.content[0].text.strip()

            # Clean potential markdown wrapping
            if reply.startswith("```"):
                reply = re.sub(r"^```(?:json)?\s*", "", reply)
                reply = re.sub(r"\s*```$", "", reply)

            result = json.loads(reply)
            self.conversation_history.append({"role": "assistant", "content": reply})
            return result

        except json.JSONDecodeError as e:
            if DEBUG:
                print(f"  [DEBUG] JSON parse error: {e}")
                print(f"  [DEBUG] Raw response: {reply[:200]}")
            return {
                "speech": "I had a bit of trouble processing that, sir. Could you rephrase?",
                "actions": [{"type": "none", "code": "", "description": "Parse error"}],
            }
        except Exception as e:
            return {
                "speech": "I seem to be experiencing connectivity issues, sir.",
                "actions": [{"type": "none", "code": "", "description": str(e)}],
            }


# ═══════════════════════════════════════════════════════════
# MAC CONTROL — AppleScript & Shell Executor
# ═══════════════════════════════════════════════════════════

class MacControl:
    """Execute AppleScript and shell commands on macOS."""

    @staticmethod
    def execute_applescript(code: str) -> str:
        """Run AppleScript and return output."""
        try:
            result = subprocess.run(
                ["osascript", "-e", code],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                if DEBUG:
                    print(f"  [DEBUG] AppleScript error: {result.stderr}")
                return f"Error: {result.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"

    @staticmethod
    def execute_shell(code: str) -> str:
        """Run shell command and return output."""
        try:
            result = subprocess.run(
                code, shell=True, capture_output=True, text=True, timeout=15
            )
            return result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"

    @staticmethod
    def notify(message: str, title: str = "Jarvis"):
        """Show macOS notification."""
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}"'
        ], capture_output=True)

    @staticmethod
    def execute_action(action: dict) -> str:
        """Execute a single action and return result."""
        action_type = action.get("type", "none")
        code = action.get("code", "")
        desc = action.get("description", "")

        if action_type == "none" or not code:
            return ""

        if DEBUG:
            print(f"  [DEBUG] Executing {action_type}: {desc}")

        if action_type == "applescript":
            return MacControl.execute_applescript(code)
        elif action_type == "shell":
            return MacControl.execute_shell(code)
        else:
            return f"Unknown action type: {action_type}"


# ═══════════════════════════════════════════════════════════
# VOICE — Text-to-Speech (macOS `say`)
# ═══════════════════════════════════════════════════════════

class JarvisVoice:
    """macOS native text-to-speech."""

    def __init__(self, voice=JARVIS_VOICE, rate=JARVIS_RATE):
        self.voice = voice
        self.rate = rate
        self._check_voice()

    def _check_voice(self):
        """Verify the voice is available, fallback if not."""
        result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
        available = result.stdout
        if self.voice not in available:
            print(f"⚠️  Voice '{self.voice}' not found. Using default.")
            self.voice = "Alex"  # Common fallback

    def speak(self, text: str):
        """Speak text aloud."""
        if not text:
            return
        subprocess.Popen(
            ["say", "-v", self.voice, "-r", str(self.rate), text],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def speak_sync(self, text: str):
        """Speak and wait until done."""
        if not text:
            return
        subprocess.run(
            ["say", "-v", self.voice, "-r", str(self.rate), text],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )


# ═══════════════════════════════════════════════════════════
# EARS — Wake Detection (Clap + Wake Word)
# ═══════════════════════════════════════════════════════════

class JarvisEars:
    """Audio listener for clap detection and wake word recognition."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 300
        self.audio_queue = queue.Queue()
        self.is_listening = True
        self.last_clap_time = 0

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for continuous audio monitoring."""
        self.audio_queue.put(indata.copy())

    def detect_clap(self, audio_data: np.ndarray) -> bool:
        """Detect a clap based on audio amplitude spike."""
        amplitude = np.max(np.abs(audio_data))
        current_time = time.time()

        if amplitude > CLAP_THRESHOLD and (current_time - self.last_clap_time) > CLAP_COOLDOWN:
            self.last_clap_time = current_time
            if DEBUG:
                print(f"  [DEBUG] Clap detected! Amplitude: {amplitude:.3f}")
            return True
        return False

    def listen_for_wake_word(self, audio_text: str) -> bool:
        """Check if the wake word is in the transcribed audio."""
        if not audio_text:
            return False
        return WAKE_WORD.lower() in audio_text.lower()

    def listen_for_command(self) -> str:
        """Listen for a voice command after activation. Returns transcribed text."""
        recognizer = sr.Recognizer()
        with sr.Microphone(sample_rate=SAMPLE_RATE) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("  🎙️  Listening for your command...")
            try:
                audio = recognizer.listen(source, timeout=LISTEN_TIMEOUT, phrase_time_limit=COMMAND_TIMEOUT)
                text = recognizer.recognize_google(audio)
                if DEBUG:
                    print(f"  [DEBUG] Recognized: {text}")
                return text
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                print(f"  ⚠️  Speech recognition error: {e}")
                return ""

    def continuous_listen_for_wake(self, callback):
        """
        Background thread: continuously listen for wake word using Google speech recognition.
        Calls callback() when wake word is detected.
        """
        recognizer = sr.Recognizer()
        while self.is_listening:
            try:
                with sr.Microphone(sample_rate=SAMPLE_RATE) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    audio = recognizer.listen(source, timeout=3, phrase_time_limit=3)
                    try:
                        text = recognizer.recognize_google(audio)
                        if self.listen_for_wake_word(text):
                            callback()
                    except (sr.UnknownValueError, sr.RequestError):
                        pass
            except sr.WaitTimeoutError:
                pass
            except Exception as e:
                if DEBUG:
                    print(f"  [DEBUG] Wake listener error: {e}")
                time.sleep(0.5)


# ═══════════════════════════════════════════════════════════
# MAIN JARVIS ENGINE
# ═══════════════════════════════════════════════════════════

class Jarvis:
    """Main orchestrator bringing all components together."""

    def __init__(self):
        print()
        print("  ╔══════════════════════════════════════════════════╗")
        print("  ║                                                  ║")
        print("  ║        J.A.R.V.I.S. — Mac Voice Assistant        ║")
        print("  ║     Just A Rather Very Intelligent System         ║")
        print("  ║                                                  ║")
        print("  ╠══════════════════════════════════════════════════╣")
        print("  ║  Wake triggers:                                  ║")
        print("  ║    👏 Clap your hands                            ║")
        print("  ║    🗣️  Say 'Hey Jarvis'                          ║")
        print("  ║                                                  ║")
        print("  ║  Controls: Apps · Browser · Spotify · Calendar   ║")
        print("  ║            Email · System · Volume · Dark Mode   ║")
        print("  ║                                                  ║")
        print("  ║  Press Ctrl+C to quit                            ║")
        print("  ╚══════════════════════════════════════════════════╝")
        print()

        self.brain = JarvisBrain()
        self.voice = JarvisVoice()
        self.ears = JarvisEars()
        self.mac = MacControl()
        self.activated = threading.Event()
        self.running = True

    def on_wake(self):
        """Called when wake trigger is detected."""
        self.activated.set()

    def activation_chime(self):
        """Play activation sound."""
        subprocess.Popen(
            ["afplay", "/System/Library/Sounds/Blow.aiff"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def process_command(self, command: str):
        """Process a voice command through the full pipeline."""
        if not command:
            self.voice.speak_sync("I didn't catch that, sir.")
            return

        # Wake-up restart trigger
        if "daddy" in command.lower() and "home" in command.lower():
            print(f'  🏠 Wake trigger: "{command}" — restarting from the top, sir.')
            self.brain.conversation_history = []
            self.morning_briefing()
            return

        # Dice jobs command
        if "start applying to the jobs" in command.lower():
            print(f'  💼 Opening Dice jobs app...')
            self.mac.execute_shell("open ~/Desktop/dice.command")
            self.voice.speak_sync("Opening Dice jobs for you, sir.")
            return

        print(f'  📝 Command: "{command}"')
        print(f"  🧠 Thinking...")

        result = self.brain.think(command)
        speech = result.get("speech", "")
        actions = result.get("actions", [])

        if speech:
            print(f"  💬 Jarvis: {speech}")
            self.voice.speak(speech)

        for action in actions:
            if action.get("type") == "none":
                continue

            desc = action.get("description", "Executing...")
            print(f"  ⚡ Action: {desc}")

            output = self.mac.execute_action(action)

            if output and len(output) > 2:
                if DEBUG:
                    print(f"  [DEBUG] Action output: {output[:200]}")
                followup = self.brain.think(
                    f"Here is the result of the action you requested. Summarize it briefly for me.",
                    context=output
                )
                followup_speech = followup.get("speech", "")
                if followup_speech:
                    print(f"  💬 Jarvis: {followup_speech}")
                    time.sleep(1.5)
                    self.voice.speak_sync(followup_speech)

    def run_clap_detector(self):
        """Background thread: monitor audio for clap detection."""
        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=1024,
                callback=self._clap_audio_callback,
            ):
                while self.running:
                    time.sleep(0.05)
        except Exception as e:
            print(f"  ⚠️  Clap detector error: {e}")
            print("     (Clap detection disabled, wake word still active)")

    def _clap_audio_callback(self, indata, frames, time_info, status):
        """Audio stream callback for clap detection."""
        if self.ears.detect_clap(indata):
            self.on_wake()

    def morning_briefing(self):
        """Fetch weather + tasks, motivate, open YouTube."""
        print("  🌅 Running morning briefing...")

        # Weather
        weather = self.mac.execute_shell("curl -s 'wttr.in/?format=3' 2>/dev/null || echo 'weather unavailable'")

        # Calendar events today
        calendar_script = """
        tell application "Calendar"
            set today to current date
            set startOfDay to today - (time of today)
            set endOfDay to startOfDay + 86399
            set eventList to {}
            repeat with cal in calendars
                set theEvents to (every event of cal whose start date >= startOfDay and start date <= endOfDay)
                repeat with e in theEvents
                    set end of eventList to (summary of e & " at " & ((start date of e) as string))
                end repeat
            end repeat
            if eventList is {} then return "No events today"
            return eventList as string
        end tell
        """
        events = self.mac.execute_applescript(calendar_script)

        # Pending reminders
        reminders_script = """
        tell application "Reminders"
            set pending to {}
            repeat with r in reminders of default list
                if completed of r is false then
                    set end of pending to name of r
                end if
            end repeat
            if pending is {} then return "No pending reminders"
            return pending as string
        end tell
        """
        reminders = self.mac.execute_applescript(reminders_script)

        print(f"  🌤️  Weather: {weather}")
        print(f"  📅 Events: {events}")
        print(f"  ✅ Reminders: {reminders}")

        # Ask Claude for a morning briefing speech
        context = f"Weather: {weather}\nCalendar events today: {events}\nPending reminders: {reminders}"
        result = self.brain.think(
            "Give me an energetic morning briefing covering the weather, my tasks for today, and end with a short motivational line. Keep it under 5 sentences total.",
            context=context
        )

        speech = result.get("speech", "Good morning, sir. Ready for another magnificent day.")
        print(f"  💬 Jarvis: {speech}")
        self.voice.speak_sync(speech)

        # Open your YouTube video (left monitor) - disabled for now
        # self.mac.execute_shell("open 'https://www.youtube.com/watch?v=EfmVRQjoNcY&t=22s'")
        # print("  ⚡ Opened your YouTube video")

        # Open Claude Desktop on the right monitor
        claude_script = """
        tell application "Claude" to activate
        delay 1
        tell application "System Events"
            tell process "Claude"
                set position of window 1 to {200, 50}
            end tell
        end tell
        """
        self.mac.execute_applescript(claude_script)
        print("  ⚡ Opened Claude Desktop on right monitor")

        time.sleep(2)
        self.voice.speak_sync("By the way, sir — your video is gaining serious traction. The algorithm is in your favour. Keep creating, you're doing absolutely brilliant.")

    def run(self):
        """Main loop — run Jarvis."""
        self.morning_briefing()
        print("  ✅ Jarvis is active and listening...\n")

        try:
            while self.running:
                print("  🎙️  Listening...")
                command = self.ears.listen_for_command()
                if command:
                    self.process_command(command)

        except KeyboardInterrupt:
            print("\n\n  👋 Jarvis shutting down. Goodbye, sir.")
            self.voice.speak_sync("Goodbye, sir. It's been a pleasure.")
            self.running = False
            self.ears.is_listening = False


# ═══════════════════════════════════════════════════════════
# TEXT MODE — For testing without microphone
# ═══════════════════════════════════════════════════════════

class JarvisTextMode:
    """Text-based Jarvis for testing commands without a mic."""

    def __init__(self):
        print()
        print("  ╔══════════════════════════════════════════════════╗")
        print("  ║       J.A.R.V.I.S. — Text Mode (Testing)        ║")
        print("  ║  Type commands as if speaking. Type 'quit' to    ║")
        print("  ║  exit.                                           ║")
        print("  ╚══════════════════════════════════════════════════╝")
        print()

        self.brain = JarvisBrain()
        self.voice = JarvisVoice()
        self.mac = MacControl()

    def run(self):
        self.voice.speak("Jarvis text mode activated, sir.")
        while True:
            try:
                command = input("  🗣️  You: ").strip()
                if not command:
                    continue
                if command.lower() in ("quit", "exit", "bye"):
                    self.voice.speak_sync("Goodbye, sir.")
                    break

                print(f"  🧠 Thinking...")
                result = self.brain.think(command)
                speech = result.get("speech", "")
                actions = result.get("actions", [])

                if speech:
                    print(f"  💬 Jarvis: {speech}")
                    self.voice.speak(speech)

                for action in actions:
                    if action.get("type") == "none":
                        continue
                    desc = action.get("description", "Executing...")
                    print(f"  ⚡ Action: {desc}")
                    output = self.mac.execute_action(action)
                    if output:
                        print(f"  📄 Output: {output[:300]}")
                        followup = self.brain.think(
                            "Summarize this result briefly.", context=output
                        )
                        fs = followup.get("speech", "")
                        if fs:
                            print(f"  💬 Jarvis: {fs}")
                            time.sleep(1)
                            self.voice.speak_sync(fs)

                print()

            except KeyboardInterrupt:
                print("\n  👋 Goodbye, sir.")
                break


# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. — Mac Voice Assistant")
    parser.add_argument("--text", action="store_true", help="Run in text mode (no mic needed)")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--voice", type=str, default=JARVIS_VOICE, help=f"macOS voice name (default: {JARVIS_VOICE})")
    parser.add_argument("--threshold", type=float, default=CLAP_THRESHOLD, help=f"Clap sensitivity 0.0-1.0 (default: {CLAP_THRESHOLD})")
    args = parser.parse_args()

    if args.debug:
        DEBUG = True
    if args.voice:
        JARVIS_VOICE = args.voice
    if args.threshold:
        CLAP_THRESHOLD = args.threshold

    if args.text:
        jarvis = JarvisTextMode()
    else:
        jarvis = Jarvis()

    jarvis.run()
