"""
Hermes integration for response generation.
Connects the Parental Coordinator Advisor to Hermes's LLM.
"""

import subprocess
import json
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent

class HermesResponseGenerator:
    """Uses Hermes Agent for strategic response generation."""
    
    def __init__(self, philosophy_docs: dict[str, str]):
        self.philosophy = philosophy_docs
        self.conversation_context: list[dict] = []
    
    def add_to_context(self, speaker: str, text: str):
        """Add a statement to the conversation context."""
        self.conversation_context.append({
            "role": "user" if speaker != "Bryan" else "assistant",
            "content": f"[{speaker}]: {text}"
        })
        # Keep context manageable
        if len(self.conversation_context) > 30:
            self.conversation_context = self.conversation_context[-30:]
    
    def generate_response(self, latest_statement: str) -> str:
        """
        Generate strategic responses using Hermes.
        
        This will be called by the main app as a subprocess or API call.
        For now, it builds the prompt that Hermes will process.
        """
        philosophy_text = "\n\n".join(
            f"## {name}\n{content[:800]}"
            for name, content in self.philosophy.items()
        )
        
        prompt = f"""You are a strategic co-pilot for Bryan during a parental coordinator meeting with Penni. The other party is Al.

BRYAN'S PARENTING PHILOSOPHY:
{philosophy_text}

CONVERSATION SO FAR:
{self._format_context()}

LATEST STATEMENT (from Al or Penni):
"{latest_statement}"

Generate 3 response options for Bryan:

1. 🛡️ DEFENSIVE — Counter false claims with documented facts
2. ⚖️ NEUTRAL — De-escalate while maintaining position  
3. 🎯 STRATEGIC — Advance Bryan's goals for this meeting

Rules:
- Every response must cite specific facts from Bryan's philosophy
- Flag any adversarial patterns (gaslighting, deflection, false equivalence)
- Keep responses to 1-3 sentences — Bryan needs to read and deliver these in real-time
- Focus on the children's wellbeing, not winning arguments
- Stay factual and documented, never emotional

Output format:
[PATTERN ALERT if applicable]
🛡️ DEFENSIVE: [response]
⚖️ NEUTRAL: [response]
🎯 STRATEGIC: [response]"""

        # In production, this calls Hermes via API or CLI
        # For now, save the prompt for Hermes to process
        prompt_file = ROOT / "sessions" / f"prompt_{int(time.time())}.txt"
        prompt_file.parent.mkdir(parents=True, exist_ok=True)
        prompt_file.write_text(prompt)
        
        return prompt
    
    def _format_context(self) -> str:
        """Format conversation context for the prompt."""
        if not self.conversation_context:
            return "(No prior conversation)"
        return "\n".join(
            f"[{m['content']}]"
            for m in self.conversation_context[-15:]
        )

# Skills integration
# This creates a Hermes skill that can be loaded for pre-meeting prep
SKILL_TEMPLATE = """---
name: parental-coordinator-prep
description: "Prepare for parental coordinator meetings — review philosophy docs, practice responses, run simulations"
version: 1.0.0
author: Bryan Dennstedt
---

# Parental Coordinator Meeting Prep

Use this skill before meetings to:
1. Review your parenting philosophy documents
2. Practice responses to anticipated attacks
3. Run adversarial simulations

## Pre-Meeting Checklist

- Load and review all docs in /Users/bryandennstedt/code/parental-coordinator-advisor/docs/philosophy/
- Identify any updates needed based on recent events
- Review meeting history for patterns and contradictions
- Run simulation: "Act as Al and present 3 challenging scenarios. I'll practice responding."
"""

def create_hermes_skill():
    """Create a Hermes skill for pre-meeting preparation."""
    skill_dir = Path.home() / ".hermes" / "skills" / "parental-coordinator-prep"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(SKILL_TEMPLATE)
    print(f"Hermes skill created: {skill_dir}")
