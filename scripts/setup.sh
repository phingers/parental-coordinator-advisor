#!/bin/bash
set -e

echo "=== Parental Coordinator Advisor Setup ==="
echo ""

# 1. Install BlackHole (virtual audio device)
echo "[1/4] Installing BlackHole..."
if ! brew list blackhole-2ch &>/dev/null; then
    brew install blackhole-2ch
    echo "✅ BlackHole installed."
    echo ""
    echo "⚠️  IMPORTANT: You must now create a Multi-Output Device:"
    echo "   1. Open Audio MIDI Setup (Applications/Utilities)"
    echo "   2. Click + → Create Multi-Output Device"
    echo "   3. Check: MacBook Speakers + BlackHole 2ch"
    echo "   4. Set as your system output before the meeting"
    echo ""
else
    echo "✅ BlackHole already installed."
fi

# 2. Python dependencies
echo "[2/4] Installing Python dependencies..."
cd "$(dirname "$0")/.."
pip install -r config/requirements.txt
echo "✅ Dependencies installed."

# 3. Create session directory
echo "[3/4] Creating session directory..."
mkdir -p sessions
echo "✅ Session directory created."

# 4. Verify docs exist
echo "[4/4] Checking philosophy docs..."
DOCS_DIR="docs/philosophy"
REQUIRED_DOCS=(
    "parenting-principles.md"
    "communication-boundaries.md"
    "child-wellbeing-priorities.md"
    "co-parenting-red-lines.md"
    "meeting-history.md"
)

ALL_EXIST=true
for doc in "${REQUIRED_DOCS[@]}"; do
    if [ -f "$DOCS_DIR/$doc" ]; then
        SIZE=$(wc -c < "$DOCS_DIR/$doc" | tr -d ' ')
        if [ "$SIZE" -lt 200 ]; then
            echo "⚠️  $doc exists but appears to be a template (${SIZE} bytes). Fill it in!"
            ALL_EXIST=false
        else
            echo "✅ $doc ($SIZE bytes)"
        fi
    else
        echo "❌ $doc missing!"
        ALL_EXIST=false
    fi
done

echo ""
if [ "$ALL_EXIST" = true ]; then
    echo "✅ All philosophy docs ready."
else
    echo "⚠️  Fill in the philosophy docs before the meeting!"
    echo "   Templates are in: $DOCS_DIR/"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Before the meeting:"
echo "  1. Fill in docs/philosophy/*.md with your actual philosophy"
echo "  2. Create Multi-Output Device in Audio MIDI Setup"
echo "  3. Set system output to the Multi-Output Device"
echo "  4. Run: python src/main.py"
