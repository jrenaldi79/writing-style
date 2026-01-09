#!/usr/bin/env python3
"""
Validation - Test generated writing assistant against held-out samples

After generating writing_assistant.md, this script:
1. Loads held-out email samples
2. Generates test emails using the prompt
3. Scores generated vs. original (embedding similarity)
4. Reports pass/fail and improvement suggestions

Usage:
    python validate.py                          # Run validation
    python validate.py --threshold 0.7          # Custom pass threshold
    python validate.py --samples 20             # Test N samples
    python validate.py --status                 # Show validation status

Requirements:
    pip install sentence-transformers numpy
    
Note: Requires an LLM API for generation (uses environment variable or config)
"""

import json
import argparse
import base64
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys

# Directories
from config import get_data_dir, get_path

DATA_DIR = get_data_dir()
VALIDATION_DIR = get_path("validation_set")
PROMPT_FILE = get_path("prompts", "writing_assistant.md")
REPORT_FILE = get_path("validation_report.json")
ENRICHED_DIR = get_path("enriched_samples")

# Default settings
DEFAULT_THRESHOLD = 0.70
DEFAULT_SAMPLES = 15


def check_dependencies():
    """Check if required packages are installed."""
    missing = []
    try:
        import sentence_transformers
    except ImportError:
        missing.append('sentence-transformers')
    try:
        import numpy
    except ImportError:
        missing.append('numpy')
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print(f"\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)


def extract_body(email_data: dict) -> str:
    """Extract plain text body from email data."""
    payload = email_data.get('payload', {})
    
    def find_text_part(parts):
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain':
                body_data = part.get('body', {}).get('data', '')
                if body_data:
                    try:
                        return base64.urlsafe_b64decode(body_data).decode('utf-8')
                    except:
                        pass
            if 'parts' in part:
                result = find_text_part(part['parts'])
                if result:
                    return result
        return None
    
    if 'parts' in payload:
        body = find_text_part(payload['parts'])
        if body:
            return body
    
    body_data = payload.get('body', {}).get('data', '')
    if body_data:
        try:
            return base64.urlsafe_b64decode(body_data).decode('utf-8')
        except:
            pass
    
    return email_data.get('snippet', '')


def get_header(email_data: dict, header_name: str) -> str:
    """Get a specific header value from email."""
    headers = email_data.get('payload', {}).get('headers', [])
    for header in headers:
        if header.get('name', '').lower() == header_name.lower():
            return header.get('value', '')
    return ''


def load_validation_samples(max_samples: int = None) -> List[Dict]:
    """Load held-out validation samples."""
    samples = []
    
    # First check validation_set directory
    if VALIDATION_DIR.exists():
        files = sorted(VALIDATION_DIR.glob('email_*.json'))
        for filepath in files[:max_samples] if max_samples else files:
            try:
                with open(filepath) as f:
                    data = json.load(f)
                samples.append({
                    'id': filepath.stem,
                    'data': data,
                    'source': 'validation_set'
                })
            except json.JSONDecodeError:
                continue
    
    # If not enough, sample from enriched (last 20%)
    if len(samples) < (max_samples or 10) and ENRICHED_DIR.exists():
        enriched_files = sorted(ENRICHED_DIR.glob('email_*.json'))
        # Take last 20% as pseudo-validation
        holdout_start = int(len(enriched_files) * 0.8)
        holdout_files = enriched_files[holdout_start:]
        
        remaining = (max_samples or 15) - len(samples)
        for filepath in holdout_files[:remaining]:
            try:
                with open(filepath) as f:
                    data = json.load(f)
                samples.append({
                    'id': filepath.stem,
                    'data': data,
                    'source': 'enriched_holdout'
                })
            except json.JSONDecodeError:
                continue
    
    return samples


def extract_context(sample: Dict) -> Dict:
    """Extract context from a sample for generation prompt."""
    data = sample['data']
    email_data = data.get('original_data', data)
    enrichment = data.get('enrichment', {})
    
    subject = get_header(email_data, 'subject')
    to_header = get_header(email_data, 'to')
    body = extract_body(email_data)
    
    # Extract first line as potential prompt
    lines = [l.strip() for l in body.split('\n') if l.strip()]
    first_line = lines[0] if lines else ''
    
    return {
        'subject': subject,
        'recipient': to_header[:50] if to_header else 'colleague',
        'recipient_type': enrichment.get('recipient_type', 'individual'),
        'audience': enrichment.get('audience', 'unknown'),
        'thread_position': enrichment.get('thread_position', 'initiating'),
        'has_bullets': enrichment.get('has_bullets', False),
        'greeting': enrichment.get('greeting', ''),
        'closing': enrichment.get('closing', ''),
        'approximate_length': len(body),
        'paragraph_count': enrichment.get('paragraph_count', 1),
        'topic_hint': first_line[:100] if first_line else subject
    }


def generate_test_email_prompt(context: Dict, prompt_content: str) -> str:
    """Create a prompt for generating a test email."""
    return f"""{prompt_content}

---

**TASK:** Write an email with the following context:

- **Subject/Topic:** {context['subject'] or context['topic_hint']}
- **Recipient Type:** {context['recipient_type']} ({context['audience']})
- **Thread Position:** {context['thread_position']}
- **Approximate Length:** {context['approximate_length']} characters
- **Include Bullets:** {'Yes' if context['has_bullets'] else 'No'}

Write ONLY the email body. Match the style specified in the writing assistant prompt above.
"""


def compute_similarity(text1: str, text2: str, model) -> float:
    """Compute cosine similarity between two texts."""
    import numpy as np
    
    embeddings = model.encode([text1, text2], normalize_embeddings=True)
    similarity = np.dot(embeddings[0], embeddings[1])
    return float(similarity)


def call_llm(prompt: str) -> Optional[str]:
    """
    Call LLM to generate text.
    
    Tries multiple methods:
    1. Anthropic API (ANTHROPIC_API_KEY)
    2. OpenAI API (OPENAI_API_KEY)
    3. Local Ollama
    """
    # Try Anthropic
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            print(f"  ⚠ Anthropic error: {e}")
    
    # Try OpenAI
    openai_key = os.environ.get('OPENAI_API_KEY')
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"  ⚠ OpenAI error: {e}")
    
    # Try local Ollama
    try:
        import requests
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={'model': 'llama2', 'prompt': prompt, 'stream': False},
            timeout=60
        )
        if response.status_code == 200:
            return response.json().get('response', '')
    except Exception:
        pass
    
    return None


def analyze_mismatch(original: str, generated: str, score: float) -> str:
    """Analyze why a generated email might not match."""
    issues = []
    
    # Length mismatch
    len_ratio = len(generated) / max(len(original), 1)
    if len_ratio < 0.5:
        issues.append("Generated too short")
    elif len_ratio > 2.0:
        issues.append("Generated too long")
    
    # Bullet mismatch
    orig_bullets = original.count('•') + original.count('- ') + original.count('* ')
    gen_bullets = generated.count('•') + generated.count('- ') + generated.count('* ')
    if orig_bullets > 0 and gen_bullets == 0:
        issues.append("Missing bullet points")
    elif orig_bullets == 0 and gen_bullets > 3:
        issues.append("Unnecessary bullet points")
    
    # Greeting check
    orig_lines = original.strip().split('\n')
    gen_lines = generated.strip().split('\n')
    if orig_lines and gen_lines:
        orig_greeting = orig_lines[0].lower()
        gen_greeting = gen_lines[0].lower()
        if ('hey' in orig_greeting or 'hi' in orig_greeting) and 'dear' in gen_greeting:
            issues.append("Tone mismatch - too formal")
        if 'dear' in orig_greeting and ('hey' in gen_greeting or 'yo' in gen_greeting):
            issues.append("Tone mismatch - too casual")
    
    # Default
    if not issues:
        if score < 0.5:
            issues.append("Significant style divergence")
        else:
            issues.append("Minor style differences")
    
    return "; ".join(issues)


def run_validation(threshold: float = DEFAULT_THRESHOLD, 
                   max_samples: int = DEFAULT_SAMPLES) -> Dict:
    """Run full validation suite."""
    check_dependencies()
    from sentence_transformers import SentenceTransformer
    
    # Check prompt exists
    if not PROMPT_FILE.exists():
        print(f"❌ Writing assistant prompt not found: {PROMPT_FILE}")
        print("   Run generation phase first.")
        return {}
    
    # Load prompt
    with open(PROMPT_FILE) as f:
        prompt_content = f.read()
    print(f"📄 Loaded prompt: {PROMPT_FILE}")
    
    # Load samples
    samples = load_validation_samples(max_samples)
    if not samples:
        print("❌ No validation samples found.")
        print("   Need either validation_set/ or enriched_samples/")
        return {}
    print(f"📧 Loaded {len(samples)} validation samples")
    
    # Load embedding model
    print("🤖 Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Check LLM availability
    print("🔌 Checking LLM availability...")
    test_response = call_llm("Say 'OK' and nothing else.")
    if not test_response:
        print("❌ No LLM available. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
        print("   Or run local Ollama: ollama serve")
        return {}
    print(f"   ✓ LLM connected")
    
    # Run validation
    print(f"\n{'═' * 50}")
    print("RUNNING VALIDATION")
    print(f"{'═' * 50}\n")
    
    results = []
    persona_scores = {}
    
    for i, sample in enumerate(samples):
        email_data = sample['data'].get('original_data', sample['data'])
        original_body = extract_body(email_data)
        context = extract_context(sample)
        
        print(f"[{i+1}/{len(samples)}] {sample['id']}...")
        
        # Generate test email
        generation_prompt = generate_test_email_prompt(context, prompt_content)
        generated = call_llm(generation_prompt)
        
        if not generated:
            print(f"  ⚠ Generation failed, skipping")
            continue
        
        # Compute similarity
        score = compute_similarity(original_body, generated, model)
        
        # Analyze if low score
        issue = analyze_mismatch(original_body, generated, score) if score < threshold else ""
        
        result = {
            'id': sample['id'],
            'score': round(score, 3),
            'passed': score >= threshold,
            'context': context,
            'issue': issue,
            'original_length': len(original_body),
            'generated_length': len(generated)
        }
        results.append(result)
        
        # Track by persona hint (recipient type + audience)
        persona_key = f"{context['recipient_type']}_{context['audience']}"
        if persona_key not in persona_scores:
            persona_scores[persona_key] = []
        persona_scores[persona_key].append(score)
        
        status = "✓" if result['passed'] else "✗"
        print(f"  {status} Score: {score:.2f} {f'({issue})' if issue else ''}")
    
    # Calculate summary
    if not results:
        print("\n❌ No results generated")
        return {}
    
    scores = [r['score'] for r in results]
    passed_count = sum(1 for r in results if r['passed'])
    overall_score = sum(scores) / len(scores)
    overall_passed = overall_score >= threshold
    
    # Find worst performers
    worst = sorted(results, key=lambda x: x['score'])[:3]
    
    # Generate suggestions
    suggestions = []
    
    # Check per-persona performance
    for persona, p_scores in persona_scores.items():
        avg = sum(p_scores) / len(p_scores)
        if avg < threshold and len(p_scores) >= 2:
            suggestions.append(f"{persona} emails need improvement (avg: {avg:.2f})")
    
    # Check common issues
    issues = [r['issue'] for r in results if r['issue']]
    if issues:
        from collections import Counter
        common_issues = Counter(issues).most_common(2)
        for issue, count in common_issues:
            if count >= 2:
                suggestions.append(f"Common issue: {issue} ({count} occurrences)")
    
    # Build report
    report = {
        'validation_run': datetime.now().isoformat(),
        'prompt_file': str(PROMPT_FILE),
        'samples_tested': len(results),
        'samples_passed': passed_count,
        'overall_score': round(overall_score, 3),
        'threshold': threshold,
        'passed': overall_passed,
        'per_persona': {
            k: {'count': len(v), 'avg_score': round(sum(v)/len(v), 3)}
            for k, v in persona_scores.items()
        },
        'worst_samples': [
            {'id': w['id'], 'score': w['score'], 'issue': w['issue']}
            for w in worst
        ],
        'suggestions': suggestions,
        'detailed_results': results
    }
    
    # Save report
    with open(REPORT_FILE, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n{'═' * 50}")
    print("VALIDATION " + ("PASSED ✓" if overall_passed else "FAILED ✗"))
    print(f"{'═' * 50}")
    print(f"Samples tested: {len(results)}")
    print(f"Samples passed: {passed_count}/{len(results)} ({passed_count/len(results)*100:.0f}%)")
    print(f"Overall score: {overall_score:.2f} (threshold: {threshold})")
    
    if persona_scores:
        print(f"\nPer-persona scores:")
        for persona, p_scores in sorted(persona_scores.items()):
            avg = sum(p_scores) / len(p_scores)
            status = "✓" if avg >= threshold else "⚠"
            print(f"  {status} {persona}: {avg:.2f} ({len(p_scores)} samples)")
    
    if worst:
        print(f"\nLowest scoring samples:")
        for w in worst:
            print(f"  • {w['id']}: {w['score']:.2f} - {w['issue']}")
    
    if suggestions:
        print(f"\n💡 Suggestions for improvement:")
        for s in suggestions:
            print(f"  • {s}")
    
    print(f"{'═' * 50}")
    print(f"\n📊 Full report saved to: {REPORT_FILE}")
    
    if not overall_passed:
        print(f"\n⚠️  Validation failed. Consider:")
        print(f"   1. Adding more examples to low-scoring personas")
        print(f"   2. Refining persona rules in writing_assistant.md")
        print(f"   3. Re-running generation with more samples")
    
    return report


def show_status():
    """Show validation status."""
    print(f"\n{'═' * 50}")
    print("VALIDATION STATUS")
    print(f"{'═' * 50}")
    
    # Check prompt
    if PROMPT_FILE.exists():
        print(f"✅ Writing assistant prompt exists")
    else:
        print(f"❌ No prompt found at {PROMPT_FILE}")
    
    # Check validation samples
    val_count = len(list(VALIDATION_DIR.glob('email_*.json'))) if VALIDATION_DIR.exists() else 0
    print(f"\nValidation samples: {val_count}")
    
    # Check last report
    if REPORT_FILE.exists():
        with open(REPORT_FILE) as f:
            report = json.load(f)
        
        print(f"\n📊 Last validation run:")
        print(f"   Date: {report.get('validation_run', 'unknown')}")
        print(f"   Score: {report.get('overall_score', 0):.2f}")
        print(f"   Result: {'PASSED' if report.get('passed') else 'FAILED'}")
        print(f"   Samples: {report.get('samples_tested', 0)}")
        
        if report.get('suggestions'):
            print(f"\n   Suggestions:")
            for s in report['suggestions'][:3]:
                print(f"   • {s}")
    else:
        print(f"\n❌ No validation report found")
        print(f"   Run: python validate.py")
    
    print(f"{'═' * 50}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Validate writing assistant against held-out samples',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate.py                    # Run validation with defaults
  python validate.py --threshold 0.75   # Custom pass threshold
  python validate.py --samples 20       # Test more samples
  python validate.py --status           # Show validation status

Requires:
  - writing_assistant.md prompt
  - Validation samples (validation_set/ or enriched_samples/)
  - LLM API key (ANTHROPIC_API_KEY or OPENAI_API_KEY) or local Ollama
        """
    )
    parser.add_argument('--threshold', type=float, default=DEFAULT_THRESHOLD,
                        help=f'Pass threshold (default: {DEFAULT_THRESHOLD})')
    parser.add_argument('--samples', type=int, default=DEFAULT_SAMPLES,
                        help=f'Number of samples to test (default: {DEFAULT_SAMPLES})')
    parser.add_argument('--status', action='store_true', help='Show validation status')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    else:
        run_validation(threshold=args.threshold, max_samples=args.samples)
