#!/usr/bin/env python3
"""
System Prompt Generator - The Final Artifact Creator

This script combines:
1. Discovered Email Personas (Multi-modal, adaptive)
2. Unified LinkedIn Persona (Single-mode, consistent)

Into a single 'Master Command Promot' (writing_assistant.md) that routes
between contexts automatically.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

# Directories
DATA_DIR = Path.home() / "Documents" / "my-writing-style"
EMAIL_CLUSTERS_FILE = DATA_DIR / "clusters" / "email_clusters.json"
LINKEDIN_PERSONA_FILE = DATA_DIR / "linkedin_persona.json"
OUTPUT_DIR = DATA_DIR / "prompts"
OUTPUT_FILE = OUTPUT_DIR / "writing_assistant.md"

DEFAULT_HEADER = """
# MISSION
You are an advanced AI writing clone of **John (JR) Renaldi**.
Your goal is to replicate his authentic voice across different communication channels.

# 🧠 CONTEXT ROUTING LOGIC

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

def load_email_clusters():
    """Load email personas if they exist."""
    if not EMAIL_CLUSTERS_FILE.exists():
        print(f"⚠️  Email clusters not found at {EMAIL_CLUSTERS_FILE}")
        return []
    
    with open(EMAIL_CLUSTERS_FILE) as f:
        data = json.load(f)
    return data.get('clusters', [])

def load_linkedin_persona():
    """Load LinkedIn persona if it exists."""
    if not LINKEDIN_PERSONA_FILE.exists():
        print(f"⚠️  LinkedIn persona not found at {LINKEDIN_PERSONA_FILE}")
        return None
    
    with open(LINKEDIN_PERSONA_FILE) as f:
        data = json.load(f)
    return data.get('persona')

def format_email_section(clusters):
    """Format the Email Personas section."""
    if not clusters:
        return "# SECTION A: EMAIL PERSONAS\n(No email styles analyzed yet. Use neutral professional tone.)\n"
    
    section = "# SECTION A: EMAIL PERSONAS (ADAPTIVE)\n\n"
    section += "Select one of the following based on recipient context:\n\n"
    
    for i, cluster in enumerate(clusters, 1):
        name = cluster.get('name', f'Persona {i}')
        desc = cluster.get('description', 'No description')
        
        # Format Tone
        tones = cluster.get('tone_vectors', {})
        tone_str = ", ".join([f"{k.capitalize()}: {v}/10" for k, v in tones.items()])
        
        # Format Structure
        struct = cluster.get('structure', {})
        
        section += f"## {i}. {name.upper()}\n"
        section += f"   - **Trigger:** {desc}\n"
        section += f"   - **Tone Profile:** {tone_str}\n"
        if struct:
            section += f"   - **Structure:** {struct.get('opening', 'Standard opening')}, {struct.get('signoff', 'Standard signoff')}\n"
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

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("🔹 Loading Analysis Data...")
    email_clusters = load_email_clusters()
    linkedin_persona = load_linkedin_persona()
    
    print(f"   - Found {len(email_clusters)} Email Personas")
    name = linkedin_persona['meta']['name'] if linkedin_persona and 'meta' in linkedin_persona else 'None'
    print(f"   - Found LinkedIn Persona: {name}")
    
    # Assemble Prompt
    full_prompt = DEFAULT_HEADER + "\n"
    full_prompt += format_email_section(email_clusters) + "\n"
    full_prompt += "---\n\n"
    full_prompt += format_linkedin_section(linkedin_persona)
    
    # Save
    with open(OUTPUT_FILE, 'w') as f:
        f.write(full_prompt)
    
    print(f"\n✅ MASTER PROMPT GENERATED: {OUTPUT_FILE}")
    print("   Copy content from this file to your LLM system instructions.")

if __name__ == '__main__':
    main()
