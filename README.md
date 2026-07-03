# Parental Coordinator Meeting Advisor

Real-time listening and response generation for parental coordinator meetings.

## What It Does
1. Captures system audio during Teams calls
2. Transcribes in real-time
3. Generates strategic responses grounded in your parenting philosophy
4. Tracks full conversation context
5. Identifies and counters adversarial positioning

## Tech Stack
- Audio capture: BlackHole (virtual audio device)
- Transcription: whisper.cpp (real-time)
- Response generation: LLM with RAG over parenting philosophy docs
- Interface: Terminal TUI with suggested responses
