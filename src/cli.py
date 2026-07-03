#!/usr/bin/env python3
"""
CLI entry point for the Parental Coordinator Advisor.
Run: python -m src.cli
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def check_blackhole():
    """Verify BlackHole is installed."""
    try:
        result = subprocess.run(
            ["brew", "list", "blackhole-2ch"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_docs():
    """Check which philosophy docs exist and are filled in."""
    docs_dir = ROOT / "docs" / "philosophy"
    if not docs_dir.exists():
        return []
    
    filled = []
    for md_file in docs_dir.glob("*.md"):
        content = md_file.read_text()
        # Check if it's more than just the template
        non_comment_lines = [
            l for l in content.split('\n') 
            if l.strip() and not l.strip().startswith('<!--') and not l.strip().startswith('>') and not l.strip().startswith('#') and l.strip() != '[Your vision here]' and '[your' not in l.lower() and '[add more]' not in l.lower() and '[name the' not in l.lower() and '[describe]' not in l.lower() and '[e.g.' not in l.lower() and '[thing' not in l.lower()
        ]
        if len(non_comment_lines) > 5:
            filled.append(md_file.stem)
    
    return filled

def main():
    print("=" * 60)
    print("  Parental Coordinator Meeting Advisor")
    print("=" * 60)
    
    # Check BlackHole
    if not check_blackhole():
        print("\n❌ BlackHole not installed.")
        print("   Run: brew install blackhole-2ch")
        print("   Then: scripts/setup.sh")
        sys.exit(1)
    
    # Check docs
    filled_docs = check_docs()
    total_docs = len(list((ROOT / "docs" / "philosophy").glob("*.md"))) if (ROOT / "docs" / "philosophy").exists() else 0
    
    print(f"\n📄 Philosophy docs: {len(filled_docs)}/{total_docs} filled in")
    if len(filled_docs) < total_docs:
        print("   ⚠️  Fill in the remaining docs for best results:")
        for md_file in (ROOT / "docs" / "philosophy").glob("*.md"):
            if md_file.stem not in filled_docs:
                print(f"      - {md_file.name}")
    
    print("\n🎤 Starting audio capture...")
    print("   (Press Ctrl+C to stop)")
    print()
    
    # Run main app
    from src.main import main as run_app
    run_app()

if __name__ == "__main__":
    main()
