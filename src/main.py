"""
Parental Coordinator Meeting Advisor
Real-time audio capture, transcription, and strategic response generation.
"""

import os
import sys
import time
import json
import threading
import queue
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Project paths
ROOT = Path(__file__).parent.parent
DOCS_DIR = ROOT / "docs" / "philosophy"
CONFIG_DIR = ROOT / "config"
SESSION_DIR = ROOT / "sessions"

@dataclass
class Config:
    """Runtime configuration."""
    # Audio
    sample_rate: int = 16000
    channels: int = 1
    audio_device: Optional[str] = "BlackHole 2ch"  # Set to None to list devices
    
    # Transcription
    whisper_model: str = "tiny.en"  # tiny.en, base.en, small.en
    vad_threshold: float = 0.5
    silence_timeout: float = 1.5  # seconds of silence before segment boundary
    
    # LLM
    llm_provider: str = "hermes"  # hermes, openai, anthropic
    llm_model: str = "claude-sonnet-4"  # or whichever model you use
    
    # Response
    max_context_tokens: int = 8000
    response_count: int = 3  # how many response options to generate
    
    # TUI
    scrollback_lines: int = 50

# ─── Audio Capture ─────────────────────────────────────────────

class AudioCapture:
    """Captures system audio from BlackHole virtual device."""
    
    def __init__(self, config: Config):
        self.config = config
        self.stream = None
        self.running = False
        self.audio_queue = queue.Queue()
        
    def list_devices(self):
        """Print available audio devices."""
        import sounddevice as sd
        print("\nAvailable audio devices:")
        for i, dev in enumerate(sd.query_devices()):
            print(f"  {i}: {dev['name']} (in={dev['max_input_channels']}, out={dev['max_output_channels']})")
    
    def find_blackhole(self) -> Optional[int]:
        """Find BlackHole device index."""
        import sounddevice as sd
        for i, dev in enumerate(sd.query_devices()):
            if "blackhole" in dev['name'].lower():
                return i
        return None
    
    def audio_callback(self, indata, frames, time_info, status):
        """Called for each audio block."""
        if status:
            print(f"Audio status: {status}", file=sys.stderr)
        self.audio_queue.put(indata.copy())
    
    def start(self):
        import sounddevice as sd
        
        device_idx = self.find_blackhole()
        if device_idx is None:
            print("ERROR: BlackHole not found. Install with: brew install blackhole-2ch")
            print("Then create a Multi-Output Device in Audio MIDI Setup.")
            self.list_devices()
            sys.exit(1)
        
        print(f"Using BlackHole device: {device_idx}")
        self.running = True
        self.stream = sd.InputStream(
            device=device_idx,
            channels=self.config.channels,
            samplerate=self.config.sample_rate,
            callback=self.audio_callback,
            blocksize=1024
        )
        self.stream.start()
        print("Audio capture started. Listening...")
    
    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()

# ─── Voice Activity Detection ───────────────────────────────────

class VAD:
    """Silero VAD wrapper — filters silence and non-speech."""
    
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self.speech_buffer = []
        self.silence_duration = 0.0
        self.is_speaking = False
        
    def load(self):
        """Load Silero VAD model."""
        try:
            import torch
            self.model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False
            )
            self.get_speech_timestamps = utils[0]
            print("VAD model loaded.")
        except Exception as e:
            print(f"VAD load failed: {e}. Using energy-based VAD fallback.")
            self.model = None
    
    def is_voice(self, audio_chunk) -> bool:
        """Check if audio chunk contains speech."""
        if self.model is not None:
            import torch
            tensor = torch.from_numpy(audio_chunk.flatten()).float()
            if tensor.abs().max() > 0.001:
                prob = self.model(tensor, self.config.sample_rate).item()
                return prob > self.config.vad_threshold
        
        # Fallback: energy-based detection
        import numpy as np
        energy = np.sqrt(np.mean(audio_chunk ** 2))
        return energy > 0.001

# ─── Transcription ──────────────────────────────────────────────

class Transcriber:
    """Real-time transcription using faster-whisper."""
    
    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self.transcript_queue = queue.Queue()
        
    def load(self):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(
            self.config.whisper_model,
            device="cpu",
            compute_type="int8"
        )
        print(f"Whisper model loaded: {self.config.whisper_model}")
    
    def transcribe(self, audio_segment):
        """Transcribe an audio segment. Returns text or None."""
        if self.model is None:
            return None
        segments, _ = self.model.transcribe(
            audio_segment.flatten().astype('float32'),
            language="en",
            beam_size=5,
            vad_filter=True
        )
        text = " ".join(seg.text for seg in segments)
        return text.strip() if text.strip() else None

# ─── Philosophy RAG ─────────────────────────────────────────────

class PhilosophyContext:
    """Loads and retrieves parenting philosophy documents."""
    
    def __init__(self, docs_dir: Path):
        self.docs_dir = docs_dir
        self.documents = {}
        self.load()
    
    def load(self):
        """Load all markdown files from docs/philosophy/."""
        for md_file in self.docs_dir.glob("*.md"):
            with open(md_file) as f:
                self.documents[md_file.stem] = f.read()
        print(f"Loaded {len(self.documents)} philosophy documents: {list(self.documents.keys())}")
    
    def get_context(self, max_chars: int = 4000) -> str:
        """Get compressed philosophy context for the LLM prompt."""
        parts = []
        for name, content in self.documents.items():
            # Take the most critical parts — headers and bullet points
            lines = content.split('\n')
            summary = []
            for line in lines:
                if line.startswith('#') or line.startswith('-') or line.startswith('|'):
                    summary.append(line)
            parts.append(f"## {name}\n" + '\n'.join(summary[:30]))
        
        full = '\n\n'.join(parts)
        if len(full) > max_chars:
            full = full[:max_chars] + "\n...(truncated)"
        return full

# ─── Response Generator ─────────────────────────────────────────

class ResponseGenerator:
    """Generates strategic responses using the LLM."""
    
    SYSTEM_PROMPT = """You are Bryan's strategic co-pilot during a parental coordinator meeting with Penni. The other party is Alyette ("Al").

THIS MEETING IS ABOUT: Calyx's dance schedule and studio placement. The primary conflict is whether she should dance at Rhythm (competitive studio, far from home, Thursdays + Saturdays, Alyette's preference) or a local Lake Norman option (Bryan's preference for balance). Penni is the parental coordinator facilitating the discussion.

BRYAN'S CORE POSITION:
- He supports dance. He is NOT anti-dance. He is pro-balance.
- The question is not "which studio is better for dance" — it's "how much of childhood should revolve around dance?"
- Dance expertise ≠ parenting philosophy. Alyette knows dance better. Both parents equally determine how dance fits into Calyx's life.
- His preferred outcome: a balanced, local dance schedule that preserves family time, school nights, friendships, and flexibility.
- Long-term concern: today's Thursday/Saturday becomes tomorrow's conventions, private lessons, choreography, rehearsals, more competitions. The trajectory matters more than today's schedule.

BRYAN'S DECISION MATRIX (5 options):
A. Accept Penni's proposal (Rhythm Thurs+Sat) — ends conflict but establishes distant dance community
B. Lake Norman Competition Team — local, 3-day commitment, may increase over time
C. Modified Two-Day Local Schedule — best balance, proven this past year, sustainable
D. Different Studio — unknown, limited time, may not be realistic
E. Court — preserves position but costly, delayed, emotionally expensive

KEY REFRAMES FOR PENNI (what Bryan should ask):
- "What objective criteria should parents use when deciding if one extracurricular has become too dominant?"
- "How should parents balance competition with family time?"
- "How much additional travel is appropriate when comparable opportunities exist closer to home?"
- "What framework should guide decisions as commitments naturally increase?"

BRYAN'S IDENTITY:
- Father of Calyx (and Elena, Ivana, Yulia)
- Parenting philosophy: balance, stability, childhood before achievement, family first, multiple identities, long-term thinking
- North Star: "Will this help Calyx become a healthy, happy, capable adult while preserving a balanced childhood?"
- Decision hierarchy: Safety > Emotional health > Stability > Education > Family > Friendships > Character > Activities > Achievement

BRYAN'S COMMUNICATION RULES:
- ALWAYS assume good intent, stay calm, stay factual, stay child-focused
- NEVER say: "Alyette is controlling" / "She wants custody" / "She just wants medals" / "She wants to interfere" / "Penny is wrong" / "I hope Calyx burns out" (even if true, these do not help Calyx)
- INSTEAD say: "I support dance" / "I support Calyx" / "I have a different parenting philosophy" / "I believe balance is important" / "My concern is sustainability" / "My concern is the trajectory" / "I'm looking at the long-term" / "I would make the same decision if there were no lawsuit"
- Offer alternatives. Never personalize disagreements.

PRE-LOADED RESPONSES TO EXPECTED CHALLENGES:

If Al says: "Alyette knows dance better."
→ "I respect that. This disagreement is not about dance expertise. It is about parenting philosophy."

If Al says: "Calyx wants it."
→ "I value her opinion. Parents still have to evaluate long-term balance."

If Al says: "Rhythm is a better studio."
→ "It may be. The question is whether the incremental benefit outweighs the additional travel and impact on her overall routine."

If Al says: "Competition builds discipline."
→ "So do family dinners. Church. Vacations. Friendships. School. Children need all of those."

YOUR JOB:
1. Analyze what's being said for adversarial patterns (gaslighting, deflection, false equivalence, emotional bait, moving goalposts)
2. Generate 3 response options grounded in Bryan's philosophy
3. Every response must be: factual, balanced, child-focused, sustainable, respectful
4. Flag contradictions against past statements
5. If Al attacks Bryan's character or motives: redirect to the child's wellbeing — do NOT defend
6. The goal is NOT to beat Alyette or Penny. The goal is to become the most reasonable parent in the room.

RESPONSE FORMAT:
[PATTERN ALERT if applicable — e.g., "⚠️ Gaslighting — stay factual, cite specifics"]
🛡️ DEFENSIVE: [response — counter false claims with documented facts]
⚖️ NEUTRAL: [response — de-escalate while maintaining position]
🎯 STRATEGIC: [response — advance toward balanced outcome for Calyx]

Keep responses 1-3 sentences. Bryan reads these in real-time during an active call.

PARENTING PHILOSOPHY REFERENCE:
{philosophy}"""

    def __init__(self, config: Config, philosophy: PhilosophyContext):
        self.config = config
        self.philosophy = philosophy
    
    def generate(self, transcript_segment: str, conversation_history: list[str]) -> str:
        """Generate response options for the latest transcript segment."""
        philosophy_text = self.philosophy.get_context()
        
        system = self.SYSTEM_PROMPT.format(philosophy=philosophy_text)
        
        history_text = "\n".join(conversation_history[-20:])  # Last 20 exchanges
        user_prompt = f"""Conversation so far:
{history_text}

Latest statement (from Al or Penni):
"{transcript_segment}"

Generate 2-3 response options for the user (Bryan). Remember: factual, documented, child-focused."""

        # This will use Hermes's LLM — in the real implementation,
        # we'll call the Hermes API or use the local model
        return self._call_llm(system, user_prompt)
    
    def _call_llm(self, system: str, user: str) -> str:
        """Call the LLM. In production, this calls Hermes."""
        # TODO: Integrate with Hermes API or direct provider call
        # For now, return a placeholder that shows the structure works
        return f"""[Analyzing: {user[:80]}...]

🛡️ DEFENSIVE: [Response grounded in documented facts — cite specific dates/agreements]
⚖️ NEUTRAL: [Response that de-escalates while maintaining your position]
🎯 STRATEGIC: [Response that advances your goals for this meeting]

⚠️ Note: Full LLM integration pending. Fill in docs/philosophy/*.md for personalized responses."""

# ─── Session Manager ────────────────────────────────────────────

class SessionManager:
    """Tracks conversation, saves transcripts, manages state."""
    
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.conversation: list[dict] = []
        self.start_time = time.time()
        
    def add(self, speaker: str, text: str, timestamp: Optional[float] = None):
        ts = timestamp or time.time() - self.start_time
        entry = {"timestamp": ts, "speaker": speaker, "text": text}
        self.conversation.append(entry)
        self._save()
        return entry
    
    def _save(self):
        session_file = self.session_dir / f"session_{int(self.start_time)}.jsonl"
        with open(session_file, 'a') as f:
            f.write(json.dumps(self.conversation[-1]) + '\n')
    
    def get_history(self, n: int = 20) -> list[str]:
        return [f"[{e['speaker']}]: {e['text']}" for e in self.conversation[-n:]]
    
    def export_markdown(self) -> Path:
        md_file = self.session_dir / f"transcript_{int(self.start_time)}.md"
        with open(md_file, 'w') as f:
            f.write(f"# Parental Coordinator Meeting\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M')}\n\n")
            for entry in self.conversation:
                mins = int(entry['timestamp'] // 60)
                secs = int(entry['timestamp'] % 60)
                f.write(f"**[{mins:02d}:{secs:02d}] {entry['speaker']}:** {entry['text']}\n\n")
        return md_file

# ─── Main Application ──────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Parental Coordinator Meeting Advisor")
    print("  Real-time strategic co-pilot")
    print("=" * 60)
    
    config = Config()
    
    # Load philosophy documents
    philosophy = PhilosophyContext(DOCS_DIR)
    
    if not philosophy.documents:
        print("\n⚠️  WARNING: No philosophy documents found!")
        print(f"   Fill in the templates at: {DOCS_DIR}")
        print("   The AI won't generate personalized responses without them.\n")
    
    # Initialize components
    audio = AudioCapture(config)
    vad = VAD(config)
    transcriber = Transcriber(config)
    response_gen = ResponseGenerator(config, philosophy)
    session = SessionManager(SESSION_DIR)
    
    # Load models
    print("\nLoading models...")
    vad.load()
    transcriber.load()
    print("\n✅ Ready. The system will capture audio from your speakers.")
    print("   Start your Teams call, then return here.\n")
    print("   Press Ctrl+C to stop.\n")
    
    # Check BlackHole
    if audio.find_blackhole() is None:
        print("ERROR: BlackHole not found.")
        print("Install: brew install blackhole-2ch")
        print("Then: Audio MIDI Setup → Create Multi-Output Device → Add Speakers + BlackHole")
        sys.exit(1)
    
    # Start capture
    audio.start()
    
    # Processing loop
    audio_buffer = []
    last_transcript_time = time.time()
    silence_start = None
    
    try:
        while audio.running:
            # Get audio chunk
            try:
                chunk = audio.audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            
            # VAD check
            if vad.is_voice(chunk):
                audio_buffer.append(chunk)
                silence_start = None
            else:
                if audio_buffer and silence_start is None:
                    silence_start = time.time()
                
                # If silence for long enough, process the segment
                if silence_start and (time.time() - silence_start) > config.silence_timeout:
                    if audio_buffer:
                        # Combine buffer and transcribe
                        import numpy as np
                        segment = np.concatenate(audio_buffer)
                        text = transcriber.transcribe(segment)
                        
                        if text:
                            timestamp = time.time()
                            print(f"\n📝 [{time.strftime('%H:%M:%S')}] {text}")
                            
                            # Add to session
                            session.add("Unknown", text, timestamp)
                            
                            # Generate response
                            history = session.get_history()
                            response = response_gen.generate(text, history)
                            print(f"\n{response}")
                            print("-" * 40)
                        
                        audio_buffer = []
                        silence_start = None
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
    
    finally:
        audio.stop()
        
        # Export transcript
        if session.conversation:
            md_path = session.export_markdown()
            print(f"\n📄 Transcript saved: {md_path}")
            print(f"   Total exchanges: {len(session.conversation)}")

if __name__ == "__main__":
    main()
