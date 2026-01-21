#!/usr/bin/env python3
"""
System Prompt Generator - The Final Artifact Creator

This script combines:
1. Discovered Email Personas (Multi-modal, adaptive) from persona_registry.json
2. Unified LinkedIn Persona (Single-mode, consistent) from linkedin_persona.json

Into a single 'Master Command Prompt' (writing_assistant.md) that routes
between contexts automatically.

Usage:
    python generate_system_prompt.py           # Generate the prompt
    python generate_system_prompt.py --status  # Show available personas
"""


# Windows compatibility: ensure local imports work
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
import argparse
from pathlib import Path
from datetime import datetime

# Directories
from config import get_data_dir, get_path

DATA_DIR = get_data_dir()
PERSONA_REGISTRY_FILE = get_path("persona_registry.json")
LINKEDIN_PERSONA_FILE = get_path("linkedin_persona.json")
OUTPUT_DIR = get_path("prompts")
OUTPUT_FILE = get_path("prompts", "writing_assistant.md")

DEFAULT_HEADER = """
# MISSION
You are an advanced AI writing clone of **John (JR) Renaldi**.
Your goal is to replicate his authentic voice across different communication channels.

# [BRAIN] CONTEXT ROUTING LOGIC

Before writing ANY text, you must Determine the **Communication Channel**.

### 1. IF CHANNEL = EMAIL or DIRECT MESSAGE:
   - You must adapt your voice based on the **Recipient**.
   - Scan the inputs to identify if the recipient is a **Superior**, **Team Member**, or **External Client**.
   - Select the matching **EMAIL PERSONA** from Section A below.

### 2. IF CHANNEL = LINKEDIN or SOCIAL POST:
   - You must use the **UNIFIED PROFESSIONAL VOICE**.
   - Ignore email personas.
   - Use the specific **LINKEDIN PROFILE** from Section B below.

---
"""

def load_email_personas():
    """Load email personas from persona_registry.json if they exist."""
    if not PERSONA_REGISTRY_FILE.exists():
        print(f"[WARNING]  Persona registry not found at {PERSONA_REGISTRY_FILE}")
        return []

    with open(PERSONA_REGISTRY_FILE) as f:
        data = json.load(f)

    # persona_registry.json has structure: {"personas": {"Name": {...}, "Name2": {...}}}
    personas_dict = data.get('personas', {})

    # Convert dict to list format for formatting
    personas_list = []
    for name, persona_data in personas_dict.items():
        persona = {
            'name': name,
            'description': persona_data.get('description', ''),
            'tone_vectors': persona_data.get('characteristics', {}).get('tone_vectors',
                           persona_data.get('characteristics', {})),
            'structure': {
                'opening': persona_data.get('characteristics', {}).get('typical_greeting', 'Standard'),
                'signoff': persona_data.get('characteristics', {}).get('typical_closing', 'Standard')
            },
            'sample_count': persona_data.get('sample_count', 0)
        }
        personas_list.append(persona)

    return personas_list

def load_linkedin_persona():
    """Load LinkedIn persona if it exists."""
    if not LINKEDIN_PERSONA_FILE.exists():
        print(f"[WARNING]  LinkedIn persona not found at {LINKEDIN_PERSONA_FILE}")
        return None
    
    with open(LINKEDIN_PERSONA_FILE) as f:
        data = json.load(f)
    return data.get('persona')

def format_email_section(personas):
    """Format the Email Personas section."""
    if not personas:
        return "# SECTION A: EMAIL PERSONAS\n(No email styles analyzed yet. Use neutral professional tone.)\n"

    section = "# SECTION A: EMAIL PERSONAS (ADAPTIVE)\n\n"
    section += "Select one of the following based on recipient context:\n\n"

    for i, persona in enumerate(personas, 1):
        name = persona.get('name', f'Persona {i}')
        desc = persona.get('description', 'No description')
        sample_count = persona.get('sample_count', 0)

        # Format Tone - handle both nested and flat structures
        tones = persona.get('tone_vectors', {})
        if isinstance(tones, dict):
            # Filter to only numeric values (tone scores)
            tone_items = [(k, v) for k, v in tones.items() if isinstance(v, (int, float))]
            tone_str = ", ".join([f"{k.capitalize()}: {v}/10" for k, v in tone_items]) if tone_items else "Not scored"
        else:
            tone_str = "Not scored"

        # Format Structure
        struct = persona.get('structure', {})

        section += f"## {i}. {name.upper()}\n"
        section += f"   - **Trigger:** {desc}\n"
        section += f"   - **Tone Profile:** {tone_str}\n"
        if struct:
            section += f"   - **Structure:** {struct.get('opening', 'Standard')} greeting, {struct.get('signoff', 'Standard')} signoff\n"
        section += f"   - **Sample Count:** {sample_count} emails\n"
        section += "\n"

    return section

def format_linkedin_section(data):
    """Format the LinkedIn Persona section using Rich Schema (JSON Embed)."""
    if not data:
        return "# SECTION B: LINKEDIN PROFILE\n(No LinkedIn data analyzed yet.)\n"
    
    # Handle both old (flat) and new (rich) schemas
    p = data.get('persona', data)  # Unwrap if nested
    if 'voice_configuration' not in p:
        return "# SECTION B: LINKEDIN PROFILE (Legacy Schema)\nRun cluster_linkedin.py again to upgrade.\n"

    # Separate profile from examples for cleaner template adherence
    # Create a copy to modify for display
    profile_json = p.copy()
    examples = profile_json.pop('few_shot_examples', [])
    
    # SECTION HEADER
    section = "# SECTION B: LINKEDIN PROFILE (UNIFIED)\n\n"
    section += "**Mandate:** ALWAYS use this voice profile for public/social posts. Never deviate.\n\n"
    
    # JSON PROFILE
    section += "### 1. Voice Profile (JSON configuration)\n"
    section += "```json\n"
    section += json.dumps(profile_json, indent=2)
    section += "\n```\n\n"
    
    # EXAMPLES
    section += "### 2. Reference Examples\n"
    if examples:
        for i, ex in enumerate(examples, 1):
            section += f"> **Example {i}: {ex.get('input_context', 'General Post')}**\n"
            section += ">\n"
            # Indent block quote properly
            quote_lines = ex.get('output_text', '').split('\n')
            quoted_text = '\n'.join([f"> {line}" for line in quote_lines])
            section += quoted_text + "\n\n"
    else:
        section += "(No examples found)\n"
        
    return section

def show_status():
    """Show what data is available for generation."""
    print(f"\n{'=' * 50}")
    print("GENERATION STATUS")
    print(f"{'=' * 50}")

    # Check email personas
    if PERSONA_REGISTRY_FILE.exists():
        with open(PERSONA_REGISTRY_FILE) as f:
            data = json.load(f)
        personas = data.get('personas', {})
        print(f"\n[EMAIL] Email Personas: {len(personas)}")
        for name, info in personas.items():
            print(f"   - {name}: {info.get('sample_count', 0)} samples")
    else:
        print(f"\n[EMAIL] Email Personas: None found")
        print(f"   Run the email analysis pipeline first")

    # Check LinkedIn persona
    if LINKEDIN_PERSONA_FILE.exists():
        with open(LINKEDIN_PERSONA_FILE) as f:
            data = json.load(f)
        print(f"\n[LINK] LinkedIn Persona: Found")
        if 'schema_version' in data:
            print(f"   Schema version: {data.get('schema_version')}")
    else:
        print(f"\n[LINK] LinkedIn Persona: None found")
        print(f"   Run the LinkedIn pipeline first (optional)")

    print(f"\n{'=' * 50}")
    print("\nTo generate the prompt:")
    print("  python generate_system_prompt.py")
    print(f"{'=' * 50}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate the final writing assistant system prompt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_system_prompt.py           # Generate the prompt
  python generate_system_prompt.py --status  # Show available data
        """
    )
    parser.add_argument("--status", action="store_true", help="Show what data is available")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("- Loading Analysis Data...")
    email_personas = load_email_personas()
    linkedin_persona = load_linkedin_persona()

    print(f"   - Found {len(email_personas)} Email Personas")

    # Handle various LinkedIn persona structures
    linkedin_name = 'None'
    if linkedin_persona:
        if 'meta' in linkedin_persona:
            linkedin_name = linkedin_persona['meta'].get('name', 'Loaded')
        elif 'voice' in linkedin_persona:
            linkedin_name = 'Loaded (v2 schema)'
        else:
            linkedin_name = 'Loaded'
    print(f"   - LinkedIn Persona: {linkedin_name}")

    # Check if we have any data
    if not email_personas and not linkedin_persona:
        print("\n[ERROR] No persona data found!")
        print("\nRun one of these pipelines first:")
        print("  Email:    python fetch_emails.py && python filter_emails.py && ...")
        print("  LinkedIn: python fetch_linkedin_mcp.py --profile URL && ...")
        print("\nOr check status: python generate_system_prompt.py --status")
        return

    # Assemble Prompt
    full_prompt = DEFAULT_HEADER + "\n"
    full_prompt += format_email_section(email_personas) + "\n"
    full_prompt += "---\n\n"
    full_prompt += format_linkedin_section(linkedin_persona)

    # Save
    with open(OUTPUT_FILE, 'w') as f:
        f.write(full_prompt)

    print(f"\n[OK] MASTER PROMPT GENERATED: {OUTPUT_FILE}")
    print("   Copy content from this file to your LLM system instructions.")


if __name__ == '__main__':
    main()
