#!/usr/bin/env python3
"""
Writing Clone Skill Generator - Creates an installable skill package

This script combines discovered Email Personas and LinkedIn Voice into
a proper skill package following the Agent Skills specification.

Output: ~/Documents/[name]-writing-clone/ skill folder

Usage:
    python generate_skill.py                    # Prompts for name
    python generate_skill.py --name john        # Uses provided name
    python generate_skill.py --status           # Show available data
    python generate_skill.py --output ~/skills  # Custom output directory
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Directories
from config import get_data_dir, get_path

DATA_DIR = get_data_dir()
PERSONA_REGISTRY_FILE = get_path("persona_registry.json")
LINKEDIN_PERSONA_FILE = get_path("linkedin_persona.json")
VALIDATION_FEEDBACK_FILE = get_path("validation_feedback.json")
VALIDATION_REPORT_FILE = get_path("validation_report.json")
SAMPLES_DIR = get_path("samples")


def load_email_personas() -> List[Dict]:
    """Load email personas from persona_registry.json."""
    if not PERSONA_REGISTRY_FILE.exists():
        return []

    with open(PERSONA_REGISTRY_FILE) as f:
        data = json.load(f)

    personas_dict = data.get('personas', {})
    personas_list = []

    for name, persona_data in personas_dict.items():
        persona = {
            'name': name,
            'description': persona_data.get('description', ''),
            'characteristics': persona_data.get('characteristics', {}),
            'sample_count': persona_data.get('sample_count', 0)
        }
        personas_list.append(persona)

    return personas_list


def load_linkedin_persona() -> Optional[Dict]:
    """Load LinkedIn persona if it exists."""
    if not LINKEDIN_PERSONA_FILE.exists():
        return None

    with open(LINKEDIN_PERSONA_FILE) as f:
        return json.load(f)


def check_validation_complete() -> Dict:
    """
    Check if validation (both phases) is complete.

    Returns:
        Dict with 'phase1_complete', 'phase2_complete', 'score', 'feedback_count'
    """
    result = {
        "phase1_complete": False,
        "phase2_complete": False,
        "score": None,
        "feedback_count": 0
    }

    # Check Phase 1 (automatic validation)
    if VALIDATION_REPORT_FILE.exists():
        try:
            with open(VALIDATION_REPORT_FILE) as f:
                report = json.load(f)
            result["phase1_complete"] = True
            result["score"] = report.get("summary", {}).get("overall_score")
        except (json.JSONDecodeError, IOError):
            pass

    # Check Phase 2 (interactive validation)
    if VALIDATION_FEEDBACK_FILE.exists():
        try:
            with open(VALIDATION_FEEDBACK_FILE) as f:
                feedback = json.load(f)
            result["feedback_count"] = len(feedback.get("feedback", []))
            result["phase2_complete"] = feedback.get("interactive_complete", False)
        except (json.JSONDecodeError, IOError):
            pass

    return result


def load_sample_emails(persona_name: str, limit: int = 3) -> List[Dict]:
    """Load sample emails for a persona for few-shot examples."""
    samples = []
    if not SAMPLES_DIR.exists():
        return samples

    for sample_file in SAMPLES_DIR.glob("*.json"):
        try:
            with open(sample_file) as f:
                sample = json.load(f)
            if sample.get('persona') == persona_name:
                content = sample.get('content', {})
                if content.get('body') or content.get('snippet'):
                    samples.append({
                        'subject': content.get('subject', ''),
                        'body': content.get('body', content.get('snippet', '')),
                        'to': content.get('to', ''),
                        'analysis': sample.get('analysis', {})
                    })
                if len(samples) >= limit:
                    break
        except:
            continue

    return samples


def generate_skill_md(user_name: str, personas: List[Dict], linkedin: Optional[Dict]) -> str:
    """Generate the main SKILL.md content."""

    # YAML frontmatter
    skill_name = f"{user_name.lower()}-writing-clone"
    description = f"Clone {user_name}'s writing voice for emails and LinkedIn posts. Use this skill when drafting emails, messages, or social posts that should match {user_name}'s authentic communication style."

    content = f"""---
name: {skill_name}
description: >
  {description}
---

# {user_name}'s Writing Voice Clone

This skill replicates {user_name}'s authentic writing voice across different communication channels.

## Context Routing

Before writing ANY text, determine the communication channel:

### Email / Direct Message
- **Adaptive voice** based on recipient type
- Select the matching persona from the table below
- See [Email Personas](references/email_personas.md) for detailed profiles and examples

### LinkedIn / Social Post
- **Unified professional voice** (consistent across all posts)
- See [LinkedIn Voice](references/linkedin_voice.md) for complete profile

---

## Quick Reference: Email Personas

"""

    if personas:
        content += "| Persona | Trigger | Tone Profile |\n"
        content += "|---------|---------|-------------|\n"

        for p in personas:
            chars = p.get('characteristics', {})
            tone_parts = []
            for key in ['formality', 'warmth', 'authority', 'directness']:
                val = chars.get(key)
                if val is not None:
                    tone_parts.append(f"{key[:4].title()}: {val}")
            tone_str = ", ".join(tone_parts) if tone_parts else "See details"

            desc = p.get('description', 'No description')[:50]
            content += f"| **{p['name']}** | {desc} | {tone_str} |\n"

        content += "\n**For detailed persona profiles with examples, see:** [references/email_personas.md](references/email_personas.md)\n"
    else:
        content += "(No email personas analyzed yet)\n"

    content += "\n---\n\n## Quick Reference: LinkedIn Voice\n\n"

    if linkedin:
        voice = linkedin.get('voice', linkedin.get('voice_configuration', {}))
        tone = voice.get('tone_vectors', {})

        content += f"- **Confidence:** {linkedin.get('confidence', 'N/A')}\n"
        content += f"- **Sample Size:** {linkedin.get('sample_size', 'N/A')} posts\n"

        if tone:
            tone_items = [f"{k}: {v}" for k, v in tone.items() if isinstance(v, (int, float))]
            if tone_items:
                content += f"- **Tone:** {', '.join(tone_items[:4])}\n"

        platform = linkedin.get('platform_rules', {})
        if platform:
            content += f"- **Hashtags:** {platform.get('hashtag_strategy', 'N/A')}\n"
            content += f"- **Length:** {platform.get('length_target', 'N/A')}\n"

        content += "\n**For complete voice profile and examples, see:** [references/linkedin_voice.md](references/linkedin_voice.md)\n"
    else:
        content += "(No LinkedIn voice analyzed yet)\n"

    content += """
---

## Usage Instructions

When asked to write content:

1. **Identify the channel:**
   - Email/DM → Use adaptive email personas
   - LinkedIn/Social → Use unified voice

2. **For emails:**
   - Determine recipient type (executive, peer, client, etc.)
   - Select matching persona from the table
   - Reference detailed profile for tone and examples

3. **For LinkedIn:**
   - Always use the unified professional voice
   - Follow platform rules (hooks, hashtags, length)
   - Match the signature phrases and emoji patterns

4. **Before writing:**
   - Read the appropriate reference file for examples
   - Match tone vectors and structural patterns
   - Use characteristic phrases naturally
"""

    return content


def generate_email_personas_md(personas: List[Dict]) -> str:
    """
    Generate detailed email personas reference file with full v2 JSON profiles embedded.

    V2 Enhanced: Embeds complete JSON profile as code block for LLM consumption,
    plus human-readable quick reference.
    """
    content = """# Email Personas - V2 Detailed Profiles

This file contains complete persona definitions with voice fingerprints, relationship calibration, guardrails, and example emails.

**Schema Version:** 2.0

---

"""

    for i, persona in enumerate(personas, 1):
        name = persona.get('name', f'Persona {i}')
        desc = persona.get('description', 'No description')
        sample_count = persona.get('sample_count', 0)

        content += f"## {i}. {name}\n\n"
        content += f"**When to use:** {desc}\n\n"
        content += f"**Sample count:** {sample_count} emails analyzed\n\n"

        # Check if v2 schema (has voice_fingerprint)
        if 'voice_fingerprint' in persona:
            # V2 Format: Embed full JSON profile
            content += "### Full Profile (v2.0)\n\n"
            content += "```json\n"

            # Create clean profile for display (remove very long example bodies)
            display_profile = json.loads(json.dumps(persona))  # Deep copy

            # Truncate example bodies to save space
            if 'example_bank' in display_profile and 'examples' in display_profile['example_bank']:
                for ex in display_profile['example_bank']['examples']:
                    if 'body' in ex and len(ex['body']) > 500:
                        ex['body'] = ex['body'][:500] + '...[truncated]'

            content += json.dumps(display_profile, indent=2)
            content += "\n```\n\n"

            # Quick reference section (human-readable summary)
            content += "### Quick Reference\n\n"

            vf = persona.get('voice_fingerprint', {})

            # Formality
            formality = vf.get('formality', {})
            if isinstance(formality, dict):
                level = formality.get('level', 'N/A')
                instruction = formality.get('instruction', '')
                content += f"- **Formality:** {level}/10 - {instruction[:100]}{'...' if len(instruction) > 100 else ''}\n"
            else:
                content += f"- **Formality:** {formality}/10\n"

            # Tone markers
            tone_markers = vf.get('tone_markers', {})
            for key in ['warmth', 'authority', 'directness']:
                marker = tone_markers.get(key, {})
                if isinstance(marker, dict):
                    level = marker.get('level', 'N/A')
                    instruction = marker.get('instruction', '')
                    content += f"- **{key.title()}:** {level}/10 - {instruction[:80]}{'...' if len(instruction) > 80 else ''}\n"
                elif marker:
                    content += f"- **{key.title()}:** {marker}/10\n"

            # Opening/closing patterns
            opening = persona.get('opening_dna', {})
            if opening.get('primary_style'):
                content += f"- **Primary Greeting:** {opening['primary_style']}\n"

            closing = persona.get('closing_dna', {})
            if closing.get('primary_style'):
                content += f"- **Primary Sign-off:** {closing['primary_style']}\n"

            # Guardrails summary
            guardrails = persona.get('guardrails', {})
            if guardrails.get('never_do'):
                content += f"- **Never Do:** {', '.join(guardrails['never_do'][:3])}\n"

            content += "\n"

        else:
            # V1 Fallback: Original format
            chars = persona.get('characteristics', {})

            content += "### Tone Vectors\n\n"
            content += "| Dimension | Score (1-10) |\n"
            content += "|-----------|-------------|\n"

            for key in ['formality', 'warmth', 'authority', 'directness']:
                val = chars.get(key, 'N/A')
                content += f"| {key.title()} | {val} |\n"

            content += "\n### Structural Patterns\n\n"
            content += f"- **Typical Greeting:** {chars.get('typical_greeting', 'N/A')}\n"
            content += f"- **Typical Closing:** {chars.get('typical_closing', 'N/A')}\n"
            content += f"- **Uses Contractions:** {chars.get('uses_contractions', 'N/A')}\n"

            if chars.get('tone'):
                content += f"- **Tone Descriptors:** {', '.join(chars.get('tone', []))}\n"

            content += "\n"

        # Load sample emails for this persona
        samples = load_sample_emails(name, limit=2)
        if samples:
            content += "### Example Emails\n\n"
            for j, sample in enumerate(samples, 1):
                content += f"**Example {j}:**\n"
                if sample.get('subject'):
                    content += f"- Subject: {sample['subject']}\n"
                body = sample.get('body', '')
                content += f"```\n{body[:500]}{'...' if len(body) > 500 else ''}\n```\n\n"

        content += "---\n\n"

    return content


def generate_linkedin_voice_md(linkedin: Dict) -> str:
    """Generate detailed LinkedIn voice reference file."""
    content = """# LinkedIn Voice - Complete Profile

This file contains the complete LinkedIn voice profile including tone vectors, platform rules, and example posts.

---

## Voice Profile

"""

    # Add JSON profile
    content += "### Full Configuration (JSON)\n\n"
    content += "```json\n"

    # Create a clean copy for display
    display_profile = {k: v for k, v in linkedin.items() if k not in ['few_shot_examples']}
    content += json.dumps(display_profile, indent=2)
    content += "\n```\n\n"

    # Voice characteristics
    voice = linkedin.get('voice', linkedin.get('voice_configuration', {}))

    if voice.get('tone_vectors'):
        content += "### Tone Vectors\n\n"
        content += "| Dimension | Score |\n"
        content += "|-----------|-------|\n"
        for k, v in voice['tone_vectors'].items():
            if isinstance(v, (int, float)):
                content += f"| {k.replace('_', ' ').title()} | {v} |\n"
        content += "\n"

    if voice.get('signature_phrases'):
        content += "### Signature Phrases\n\n"
        for phrase in voice['signature_phrases']:
            content += f"- \"{phrase}\"\n"
        content += "\n"

    # Platform rules
    platform = linkedin.get('platform_rules', {})
    if platform:
        content += "### Platform Rules\n\n"
        for key, value in platform.items():
            content += f"- **{key.replace('_', ' ').title()}:** {value}\n"
        content += "\n"

    # Guardrails
    guardrails = linkedin.get('guardrails', {})
    if guardrails:
        content += "### Guardrails (What NOT to do)\n\n"
        if guardrails.get('never_do'):
            content += "**Never:**\n"
            for item in guardrails['never_do']:
                content += f"- {item}\n"
        if guardrails.get('forbidden_phrases'):
            content += "\n**Forbidden phrases:**\n"
            for phrase in guardrails['forbidden_phrases']:
                content += f"- \"{phrase}\"\n"
        content += "\n"

    # Few-shot examples
    examples = linkedin.get('few_shot_examples', [])
    if not examples:
        # Try alternate location
        examples = linkedin.get('voice', {}).get('few_shot_examples', [])

    if examples:
        content += "---\n\n## Example Posts\n\n"
        for i, ex in enumerate(examples, 1):
            context = ex.get('input_context', 'General Post')
            text = ex.get('output_text', '')
            content += f"### Example {i}: {context}\n\n"
            content += f"```\n{text}\n```\n\n"

    return content


def generate_skill(user_name: str, output_dir: Path) -> Path:
    """Generate the complete skill package."""

    skill_name = f"{user_name.lower()}-writing-clone"
    skill_dir = output_dir / skill_name
    references_dir = skill_dir / "references"

    # Create directories
    skill_dir.mkdir(parents=True, exist_ok=True)
    references_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    personas = load_email_personas()
    linkedin = load_linkedin_persona()

    print(f"📊 Loading persona data...")
    print(f"   Email personas: {len(personas)}")
    print(f"   LinkedIn voice: {'Yes' if linkedin else 'No'}")

    # Generate SKILL.md
    skill_content = generate_skill_md(user_name, personas, linkedin)
    skill_file = skill_dir / "SKILL.md"
    with open(skill_file, 'w') as f:
        f.write(skill_content)
    print(f"   ✓ Created SKILL.md")

    # Generate email personas reference
    if personas:
        email_content = generate_email_personas_md(personas)
        email_file = references_dir / "email_personas.md"
        with open(email_file, 'w') as f:
            f.write(email_content)
        print(f"   ✓ Created references/email_personas.md")

    # Generate LinkedIn voice reference
    if linkedin:
        linkedin_content = generate_linkedin_voice_md(linkedin)
        linkedin_file = references_dir / "linkedin_voice.md"
        with open(linkedin_file, 'w') as f:
            f.write(linkedin_content)
        print(f"   ✓ Created references/linkedin_voice.md")

    return skill_dir


def show_status():
    """Show what data is available for skill generation."""
    print(f"\n{'═' * 50}")
    print("SKILL GENERATION STATUS")
    print(f"{'═' * 50}")

    # Check email personas
    if PERSONA_REGISTRY_FILE.exists():
        with open(PERSONA_REGISTRY_FILE) as f:
            data = json.load(f)
        personas = data.get('personas', {})
        print(f"\n📧 Email Personas: {len(personas)}")
        for name, info in personas.items():
            print(f"   • {name}: {info.get('sample_count', 0)} samples")
    else:
        print(f"\n📧 Email Personas: None found")

    # Check LinkedIn persona
    if LINKEDIN_PERSONA_FILE.exists():
        with open(LINKEDIN_PERSONA_FILE) as f:
            data = json.load(f)
        print(f"\n🔗 LinkedIn Voice: Found")
        print(f"   Confidence: {data.get('confidence', 'N/A')}")
        print(f"   Sample size: {data.get('sample_size', 'N/A')}")
    else:
        print(f"\n🔗 LinkedIn Voice: None found")

    print(f"\n{'═' * 50}")
    print("\nTo generate the skill:")
    print("  python generate_skill.py --name <your-name>")
    print(f"{'═' * 50}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a writing clone skill package",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_skill.py                    # Prompts for name
  python generate_skill.py --name john        # Uses provided name
  python generate_skill.py --status           # Show available data
  python generate_skill.py --output ~/skills  # Custom output directory
        """
    )
    parser.add_argument("--name", type=str, help="Your name for the skill (e.g., 'john')")
    parser.add_argument("--output", type=str, default=str(Path.home() / "Documents"),
                        help="Output directory (default: ~/Documents)")
    parser.add_argument("--status", action="store_true", help="Show available data")
    parser.add_argument("--skip-validation-check", action="store_true",
                        help="Skip interactive validation check (not recommended)")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    # Get user name (required CLI argument)
    user_name = args.name
    if not user_name:
        print("❌ Name is required. Use --name <your-name>")
        print("   Example: python generate_skill.py --name john")
        sys.exit(1)

    # Validate name
    if not user_name.replace('-', '').replace('_', '').isalnum():
        print("❌ Name should only contain letters, numbers, hyphens, or underscores")
        return

    output_dir = Path(args.output)

    # Check validation status (unless skipped)
    if not args.skip_validation_check:
        validation = check_validation_complete()

        if not validation["phase1_complete"]:
            print(f"\n{'═' * 60}")
            print("❌ VALIDATION NOT COMPLETE")
            print(f"{'═' * 60}")
            print("\nYou must run validation before generating the skill.")
            print("\nRun:")
            print("  1. python prepare_validation.py")
            print("  2. python validate_personas.py --auto")
            print("  3. python validate_personas.py --review  (interactive)")
            print(f"{'═' * 60}\n")
            sys.exit(1)

        if not validation["phase2_complete"]:
            print(f"\n{'═' * 60}")
            print("⚠️  INTERACTIVE VALIDATION NOT COMPLETE")
            print(f"{'═' * 60}")
            print(f"""
Phase 1 (automatic) validation is complete with score: {validation['score']}/100
But interactive validation (Phase 2) was not completed.

Without interactive validation:
  • Personas may not sound like you in practice
  • You'll spend more time fixing issues post-generation
  • Lower quality output

RECOMMENDED: Complete interactive validation first:
  python validate_personas.py --review
  python validate_personas.py --feedback <email_id> --sounds-like-me true/false
  python validate_personas.py --suggestions

TO PROCEED ANYWAY (not recommended):
  python generate_skill.py --name {user_name} --skip-validation-check
""")
            print(f"{'═' * 60}\n")
            sys.exit(1)

    # Check if we have any data
    personas = load_email_personas()
    linkedin = load_linkedin_persona()

    if not personas and not linkedin:
        print("❌ No persona data found!")
        print("\nRun one of these pipelines first:")
        print("  Email:    python fetch_emails.py && ...")
        print("  LinkedIn: python fetch_linkedin_mcp.py --profile URL && ...")
        print("\nOr check status: python generate_skill.py --status")
        return

    # Generate the skill
    print(f"\n{'═' * 60}")
    print("GENERATING WRITING CLONE SKILL")
    print(f"{'═' * 60}\n")

    skill_dir = generate_skill(user_name, output_dir)

    # Success message with installation instructions
    print(f"\n{'═' * 60}")
    print("✅ WRITING CLONE SKILL GENERATED")
    print(f"{'═' * 60}")
    print(f"\nSkill created at: {skill_dir}")
    print(f"\nFiles generated:")
    for f in skill_dir.rglob("*"):
        if f.is_file():
            print(f"   • {f.relative_to(skill_dir)}")

    print(f"\n{'─' * 60}")
    print("📦 TO INSTALL THIS SKILL:")
    print(f"{'─' * 60}")
    print("\nOption 1: Ask the LLM to install it")
    print(f"   START A NEW CHAT and say:")
    print(f"   'Install my writing clone skill from {skill_dir}'")
    print()
    print("Option 2: Manual installation")
    print(f"   cp -r {skill_dir} ~/.claude/skills/")
    print(f"{'═' * 60}\n")


if __name__ == '__main__':
    main()
