#!/bin/bash
# ═══════════════════════════════════════════════════════════
# J.A.R.V.I.S. Setup Script for macOS
# ═══════════════════════════════════════════════════════════

set -e

echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║     J.A.R.V.I.S. — Installation Script           ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "❌ This script requires macOS."
    exit 1
fi

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Install from https://python.org"
    exit 1
fi

echo "📦 Installing Python dependencies..."
pip3 install --user anthropic sounddevice numpy SpeechRecognition pyaudio 2>/dev/null || {
    echo ""
    echo "⚠️  If pyaudio fails, install portaudio first:"
    echo "   brew install portaudio"
    echo "   pip3 install pyaudio"
    echo ""
    pip3 install --user anthropic sounddevice numpy SpeechRecognition
}

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo ""
    echo "🔑 ANTHROPIC_API_KEY not set. Add it to your shell profile:"
    echo ""
    echo "   echo 'export ANTHROPIC_API_KEY=\"your-key-here\"' >> ~/.zshrc"
    echo "   source ~/.zshrc"
    echo ""
fi

# Grant microphone permissions reminder
echo "🎤 IMPORTANT: macOS Microphone Permission"
echo "   When you first run Jarvis, macOS will ask for microphone access."
echo "   Click 'Allow' — Jarvis needs this for voice commands and clap detection."
echo ""

# List available voices
echo "🗣️  Available high-quality macOS voices:"
say -v '?' 2>/dev/null | grep -E "(Daniel|Alex|Samantha|Ava|Tom|Moira|Rishi)" | head -10
echo ""
echo "   Change voice with: python3 jarvis.py --voice 'Alex'"
echo ""

echo "✅ Setup complete!"
echo ""
echo "  ┌─────────────────────────────────────────────────┐"
echo "  │  QUICK START:                                   │"
echo "  │                                                 │"
echo "  │  Full voice mode:                               │"
echo "  │    python3 jarvis.py                            │"
echo "  │                                                 │"
echo "  │  Text mode (test without mic):                  │"
echo "  │    python3 jarvis.py --text                     │"
echo "  │                                                 │"
echo "  │  Debug mode:                                    │"
echo "  │    python3 jarvis.py --debug                    │"
echo "  │                                                 │"
echo "  │  Adjust clap sensitivity:                       │"
echo "  │    python3 jarvis.py --threshold 0.4            │"
echo "  └─────────────────────────────────────────────────┘"
echo ""
