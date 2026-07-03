# Parental Coordinator Meeting Advisor — Architecture

## Problem

During parental coordinator meetings, you face:
1. **High-speed adversarial positioning** from the other party (Al)
2. **Emotional pressure** that makes strategic thinking difficult in the moment
3. **Information asymmetry** — they prepare, you react
4. **Recording constraints** — everything you say becomes evidence

## Solution

A real-time AI co-pilot that:
- **Listens** to the conversation through your MacBook speakers
- **Transcribes** every word in real-time
- **Analyzes** for adversarial patterns, inconsistencies, and openings
- **Generates** 2-3 response options grounded in your parenting philosophy
- **Remembers** everything said, cross-referencing past statements

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TEAMS CALL (Audio Output)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │   BlackHole    │  Virtual audio device
                    │  (system loop) │  captures speaker output
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  Audio Capture │  sounddevice / pyaudio
                    │  (16kHz mono)  │  reads BlackHole stream
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  VAD Filter    │  Silero VAD
                    │  (voice only)  │  strips silence/noise
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  Transcription │  whisper.cpp
                    │  (streaming)   │  ~200ms latency
                    └───────┬────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
     ┌────────▼──────┐ ┌───▼────┐ ┌──────▼──────────┐
     │ Conversation  │ │Pattern │ │ Parenting       │
     │ History       │ │Detector│ │ Philosophy Docs │
     │ (sliding win) │ │        │ │ (RAG context)   │
     └────────┬──────┘ └───┬────┘ └──────┬──────────┘
              │             │             │
              └─────────────┼─────────────┘
                            │
                    ┌───────▼────────┐
                    │  LLM Response  │  Hermes / OpenAI / Claude
                    │  Generator     │  Strategic response engine
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  TUI Display   │  Terminal interface
                    │  (responses)   │  2-3 options + context
                    └────────────────┘
```

## Components

### 1. Audio Pipeline (`src/audio/`)
- **`capture.py`** — Streams system audio from BlackHole at 16kHz mono
- **`vad.py`** — Voice Activity Detection, filters non-speech
- **`buffer.py`** — Ring buffer for smooth streaming to transcription

### 2. Transcription (`src/transcription/`)
- **`whisper_stream.py`** — whisper.cpp streaming with partial results
- **`speaker_diarization.py`** — Identifies who is speaking (you vs Al vs Penni)

### 3. Analysis Engine (`src/analysis/`)
- **`pattern_detector.py`** — Identifies adversarial patterns:
  - Gaslighting ("that never happened")
  - Deflection ("but what about when you...")
  - False equivalence ("you did X too")
  - Strawman arguments
  - Shifting goalposts
- **`contradiction_tracker.py`** — Cross-references statements against history
- **`sentiment.py`** — Detects escalation, emotional manipulation

### 4. Response Generator (`src/response/`)
- **`generator.py`** — LLM-powered response generation
  - Grounded in your parenting philosophy
  - Cites specific past statements for contradiction
  - Offers 2-3 options: Defensive, Neutral, Strategic
  - Focuses on documented facts, not emotional reactions
- **`philosophy_rag.py`** — Retrieves relevant parenting philosophy context

### 5. TUI (`src/tui/`)
- **`app.py`** — Terminal UI showing:
  - Live transcription stream (scrolling)
  - Current speaker indicator
  - Pattern alerts ("⚠️ Gaslighting detected")
  - Suggested responses (2-3 options)
  - Quick-reference philosophy cards

### 6. Session Management (`src/session/`)
- **`recorder.py`** — Saves full transcript for post-meeting review
- **`timeline.py`** — Timestamps all statements for evidence
- **`export.py`** — Export to markdown for your records

## Response Modes

The system generates responses in three styles:

| Mode | When to Use | Example |
|------|------------|---------|
| **🛡️ Defensive** | Counter false claims with facts | "That's not accurate. On June 3rd, the agreement stated..." |
| **⚖️ Neutral** | De-escalate, buy time | "I'd like to understand your concern better. Can you clarify..." |
| **🎯 Strategic** | Advance your position | "Since we've established X, I propose we move forward with Y..." |

## Parenting Philosophy Integration

Your philosophy docs live in `docs/philosophy/`. They're loaded as RAG context and influence every response:

- `parenting-principles.md` — Core beliefs, non-negotiables
- `communication-boundaries.md` — What you will/won't engage with
- `child-wellbeing-priorities.md` — What matters most for the kids
- `co-parenting-red-lines.md` — Hard boundaries, deal-breakers
- `meeting-history.md` — Past agreements, broken promises, patterns

The LLM uses these to ensure every suggested response aligns with your values and documented history.

## Adversarial Pattern Detection

The system watches for these specific patterns and alerts you:

| Pattern | Alert | Suggested Response |
|---------|-------|-------------------|
| Gaslighting | ⚠️ "Claim contradicts documented history" | Cite specific date/fact |
| Deflection | ⚠️ "Topic shift detected" | "Let's stay on [original topic]" |
| False equivalence | ⚠️ "Invalid comparison" | "Those are different situations because..." |
| Emotional bait | ⚠️ "Escalation attempt" | Stay factual, don't match energy |
| Moving goalposts | ⚠️ "Standard changed" | "Earlier you said X, now you're saying Y" |

## Setup

```bash
# 1. Install BlackHole (virtual audio device)
brew install blackhole-2ch

# 2. Set up multi-output device (so you can hear + capture)
# System Settings → Audio MIDI Setup → Create Multi-Output Device
# Add: MacBook Speakers + BlackHole 2ch

# 3. Install Python dependencies
pip install sounddevice numpy silero-vad faster-whisper rich textual

# 4. Install whisper.cpp
brew install whisper-cpp

# 5. Run
python src/main.py
```

## Pre-Meeting Checklist

- [ ] Philosophy docs updated in `docs/philosophy/`
- [ ] BlackHole installed and configured
- [ ] Multi-output device created
- [ ] Test run with sample audio
- [ ] Battery charged (MacBook)
- [ ] Do Not Disturb enabled
- [ ] Recording consent verified (one-party state: NC is one-party consent) ✅
