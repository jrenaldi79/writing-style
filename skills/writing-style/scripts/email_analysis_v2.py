#!/usr/bin/env python3
"""
Email Analysis V2 - Deterministic metrics extraction

Provides Python-based analysis for email persona v2 schema fields.
All functions in this module are deterministic (no LLM calls).

Usage:
    from email_analysis_v2 import compute_deterministic_metrics
    metrics = compute_deterministic_metrics(emails)
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from collections import Counter
from datetime import datetime

# Try to import NLTK for sentence tokenization
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


def _ensure_nltk_data():
    """Download NLTK data if needed."""
    if not NLTK_AVAILABLE:
        return
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        try:
            nltk.download('punkt', quiet=True)
        except Exception:
            pass
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        try:
            nltk.download('punkt_tab', quiet=True)
        except Exception:
            pass


def _simple_sentence_split(text: str) -> List[str]:
    """Simple sentence splitter fallback when NLTK is not available."""
    # Split on sentence-ending punctuation followed by space and capital
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [s.strip() for s in sentences if s.strip()]


def _get_body(email: Dict) -> str:
    """Extract body from email dict."""
    if "original_data" in email:
        return email["original_data"].get("body", "") or ""
    return email.get("body", "") or ""


def _get_subject(email: Dict) -> str:
    """Extract subject from email dict."""
    if "original_data" in email:
        return email["original_data"].get("subject", "") or ""
    return email.get("subject", "") or ""


# =============================================================================
# RHYTHM ANALYSIS
# =============================================================================

def analyze_rhythm(emails: List[Dict]) -> Dict:
    """
    Calculate rhythm metrics across all emails.

    Returns:
        {
            "avg_words_per_sentence": float,
            "sentence_length_distribution": {
                "lt_8_words_ratio": float,
                "8_to_20_words_ratio": float,
                "gt_20_words_ratio": float
            },
            "paragraphing": {
                "avg_sentences_per_paragraph": float,
                "uses_single_sentence_paragraphs": bool,
                "visual_density": str
            }
        }
    """
    if not emails:
        return {
            "avg_words_per_sentence": 0,
            "sentence_length_distribution": {
                "lt_8_words_ratio": 0,
                "8_to_20_words_ratio": 0,
                "gt_20_words_ratio": 0
            },
            "paragraphing": {
                "avg_sentences_per_paragraph": 0,
                "uses_single_sentence_paragraphs": False,
                "visual_density": "medium"
            }
        }

    _ensure_nltk_data()

    all_sentence_lengths = []
    paragraph_sentence_counts = []
    single_sentence_para_count = 0
    total_paragraphs = 0

    for email in emails:
        body = _get_body(email)
        if not body:
            continue

        # Split into paragraphs
        paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]

        for para in paragraphs:
            # Skip very short lines (likely greetings/closings)
            if len(para) < 20:
                continue

            # Tokenize sentences
            if NLTK_AVAILABLE:
                try:
                    sentences = sent_tokenize(para)
                except Exception:
                    sentences = _simple_sentence_split(para)
            else:
                sentences = _simple_sentence_split(para)

            if not sentences:
                continue

            total_paragraphs += 1
            paragraph_sentence_counts.append(len(sentences))

            if len(sentences) == 1:
                single_sentence_para_count += 1

            for sent in sentences:
                words = sent.split()
                if words:
                    all_sentence_lengths.append(len(words))

    if not all_sentence_lengths:
        return {
            "avg_words_per_sentence": 0,
            "sentence_length_distribution": {
                "lt_8_words_ratio": 0,
                "8_to_20_words_ratio": 0,
                "gt_20_words_ratio": 0
            },
            "paragraphing": {
                "avg_sentences_per_paragraph": 0,
                "uses_single_sentence_paragraphs": False,
                "visual_density": "medium"
            }
        }

    avg_words = sum(all_sentence_lengths) / len(all_sentence_lengths)

    # Sentence length distribution
    short = sum(1 for l in all_sentence_lengths if l < 8)
    medium = sum(1 for l in all_sentence_lengths if 8 <= l <= 20)
    long = sum(1 for l in all_sentence_lengths if l > 20)
    total = len(all_sentence_lengths)

    # Paragraphing
    avg_sent_per_para = (sum(paragraph_sentence_counts) / len(paragraph_sentence_counts)
                         if paragraph_sentence_counts else 0)
    uses_single = (single_sentence_para_count / total_paragraphs > 0.2
                   if total_paragraphs > 0 else False)

    # Visual density based on avg sentences per paragraph
    if avg_sent_per_para <= 2:
        visual_density = "low"
    elif avg_sent_per_para <= 4:
        visual_density = "medium"
    else:
        visual_density = "high"

    return {
        "avg_words_per_sentence": round(avg_words, 1),
        "sentence_length_distribution": {
            "lt_8_words_ratio": round(short / total, 2) if total else 0,
            "8_to_20_words_ratio": round(medium / total, 2) if total else 0,
            "gt_20_words_ratio": round(long / total, 2) if total else 0
        },
        "paragraphing": {
            "avg_sentences_per_paragraph": round(avg_sent_per_para, 1),
            "uses_single_sentence_paragraphs": uses_single,
            "visual_density": visual_density
        }
    }


# =============================================================================
# FORMATTING ANALYSIS
# =============================================================================

# Patterns for bullet/list detection
BULLET_PATTERN = re.compile(r'^[\s]*[-*-]\s+', re.MULTILINE)
NUMBERED_PATTERN = re.compile(r'^[\s]*\d+[.)]\s+', re.MULTILINE)


def analyze_formatting(emails: List[Dict]) -> Dict:
    """
    Detect formatting patterns via regex.

    Returns:
        {
            "uses_bullets_rate": float,
            "uses_numbering_rate": float,
            "avg_paragraphs_per_email": float,
            "line_break_frequency": str
        }
    """
    if not emails:
        return {
            "uses_bullets_rate": 0,
            "uses_numbering_rate": 0,
            "avg_paragraphs_per_email": 0,
            "line_break_frequency": "medium"
        }

    bullets_count = 0
    numbered_count = 0
    paragraph_counts = []

    for email in emails:
        body = _get_body(email)
        if not body:
            continue

        # Check for bullets
        if BULLET_PATTERN.search(body):
            bullets_count += 1

        # Check for numbered lists
        if NUMBERED_PATTERN.search(body):
            numbered_count += 1

        # Count paragraphs
        paragraphs = [p for p in body.split('\n\n') if p.strip()]
        paragraph_counts.append(len(paragraphs))

    total = len(emails)
    avg_paragraphs = sum(paragraph_counts) / len(paragraph_counts) if paragraph_counts else 0

    # Line break frequency based on avg paragraphs
    if avg_paragraphs <= 2:
        line_break_freq = "low"
    elif avg_paragraphs <= 4:
        line_break_freq = "medium"
    else:
        line_break_freq = "high"

    return {
        "uses_bullets_rate": round(bullets_count / total, 2) if total else 0,
        "uses_numbering_rate": round(numbered_count / total, 2) if total else 0,
        "avg_paragraphs_per_email": round(avg_paragraphs, 1),
        "line_break_frequency": line_break_freq
    }


# =============================================================================
# GREETING/CLOSING EXTRACTION
# =============================================================================

# Common greeting patterns
GREETING_PATTERNS = [
    (r'^Hey\s+(\w+),?', "Hey {name},"),
    (r'^Hi\s+(\w+),?', "Hi {name},"),
    (r'^Hello\s+(\w+),?', "Hello {name},"),
    (r'^Dear\s+(\w+),?', "Dear {name},"),
    (r'^Hey,?$', "Hey,"),
    (r'^Hi,?$', "Hi,"),
    (r'^Hello,?$', "Hello,"),
    (r'^Team,?$', "Team,"),
    (r'^All,?$', "All,"),
    (r'^Everyone,?$', "Everyone,"),
]

# Common closing patterns
CLOSING_PATTERNS = [
    (r'^Thanks,?$', "Thanks,"),
    (r'^Thank you,?$', "Thank you,"),
    (r'^Best,?$', "Best,"),
    (r'^Best regards,?$', "Best regards,"),
    (r'^Regards,?$', "Regards,"),
    (r'^Cheers,?$', "Cheers,"),
    (r'^Appreciate it,?$', "Appreciate it,"),
    (r'^-\s*\w+$', "-{name}"),
    (r'^—\s*\w+$', "-{name}"),
]


def extract_greeting_distribution(emails: List[Dict]) -> Dict:
    """
    Extract greeting patterns from first lines.

    Returns:
        {
            "distribution": {pattern: ratio},
            "primary_style": str
        }
    """
    if not emails:
        return {
            "distribution": {},
            "primary_style": "Hi {name},"
        }

    greeting_counts = Counter()
    total_greetings = 0

    for email in emails:
        body = _get_body(email)
        if not body:
            continue

        # Get first non-empty line
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        if not lines:
            continue

        first_line = lines[0]

        # Try to match greeting patterns
        matched = False
        for pattern, label in GREETING_PATTERNS:
            if re.match(pattern, first_line, re.IGNORECASE):
                greeting_counts[label] += 1
                total_greetings += 1
                matched = True
                break

        if not matched:
            # Check for simple name greeting
            if re.match(r'^[A-Z][a-z]+,?$', first_line):
                greeting_counts["{name},"] += 1
                total_greetings += 1

    if total_greetings == 0:
        return {
            "distribution": {"No greeting detected": 1.0},
            "primary_style": "Hi {name},"
        }

    distribution = {k: round(v / total_greetings, 2) for k, v in greeting_counts.most_common()}
    primary = greeting_counts.most_common(1)[0][0] if greeting_counts else "Hi {name},"

    return {
        "distribution": distribution,
        "primary_style": primary
    }


def extract_closing_distribution(emails: List[Dict]) -> Dict:
    """
    Extract sign-off patterns from last lines.

    Returns:
        {
            "distribution": {pattern: ratio},
            "primary_style": str,
            "uses_signature_block": bool
        }
    """
    if not emails:
        return {
            "distribution": {},
            "primary_style": "Best,",
            "uses_signature_block": False
        }

    closing_counts = Counter()
    total_closings = 0
    signature_block_count = 0

    for email in emails:
        body = _get_body(email)
        if not body:
            continue

        # Get last few non-empty lines
        lines = [l.strip() for l in body.split('\n') if l.strip()]
        if not lines:
            continue

        # Check last 5 lines for closing patterns
        check_lines = lines[-5:] if len(lines) >= 5 else lines

        for line in reversed(check_lines):
            matched = False
            for pattern, label in CLOSING_PATTERNS:
                if re.match(pattern, line, re.IGNORECASE):
                    closing_counts[label] += 1
                    total_closings += 1
                    matched = True
                    break

            if matched:
                break

        # Check for signature block (multiple lines after closing with name/title/email)
        if len(lines) >= 3:
            last_three = '\n'.join(lines[-3:])
            if re.search(r'@\w+\.\w+|^\d{3}[-.\s]?\d{3}[-.\s]?\d{4}$', last_three, re.MULTILINE):
                signature_block_count += 1

    if total_closings == 0:
        return {
            "distribution": {"No closing detected": 1.0},
            "primary_style": "Best,",
            "uses_signature_block": signature_block_count > len(emails) * 0.3
        }

    distribution = {k: round(v / total_closings, 2) for k, v in closing_counts.most_common()}
    primary = closing_counts.most_common(1)[0][0] if closing_counts else "Best,"

    return {
        "distribution": distribution,
        "primary_style": primary,
        "uses_signature_block": signature_block_count > len(emails) * 0.3
    }


# =============================================================================
# SUBJECT LINE ANALYSIS
# =============================================================================

def analyze_subject_lines(emails: List[Dict]) -> Dict:
    """
    Analyze subject line patterns.

    Returns:
        {
            "length_chars_range": [min, max],
            "avg_word_count": float,
            "casing_distribution": {type: ratio},
            "common_prefixes": [str],
            "uses_brackets_rate": float
        }
    """
    if not emails:
        return {
            "length_chars_range": [0, 0],
            "avg_word_count": 0,
            "casing_distribution": {
                "title_case": 0,
                "sentence_case": 0,
                "all_caps": 0,
                "lowercase": 0
            },
            "common_prefixes": [],
            "uses_brackets_rate": 0
        }

    lengths = []
    word_counts = []
    casing_counts = Counter()
    prefix_counts = Counter()
    brackets_count = 0

    for email in emails:
        subject = _get_subject(email)
        if not subject:
            continue

        # Length
        lengths.append(len(subject))

        # Word count
        words = subject.split()
        word_counts.append(len(words))

        # Detect casing
        # Remove prefixes for casing analysis
        clean_subject = re.sub(r'^(Re:|Fwd:|FYI:|FW:)\s*', '', subject, flags=re.IGNORECASE).strip()

        if clean_subject:
            if clean_subject.isupper():
                casing_counts["all_caps"] += 1
            elif clean_subject.islower():
                casing_counts["lowercase"] += 1
            elif clean_subject[0].isupper() and not clean_subject.istitle():
                casing_counts["sentence_case"] += 1
            else:
                casing_counts["title_case"] += 1

        # Detect prefixes
        prefix_match = re.match(r'^(Re:|Fwd:|FYI:|FW:|Action:|Update:|Reminder:)', subject, re.IGNORECASE)
        if prefix_match:
            prefix_counts[prefix_match.group(1)] += 1

        # Detect brackets
        if re.search(r'\[.*?\]', subject):
            brackets_count += 1

    total = len([e for e in emails if _get_subject(e)])

    if not lengths:
        return {
            "length_chars_range": [0, 0],
            "avg_word_count": 0,
            "casing_distribution": {
                "title_case": 0,
                "sentence_case": 0,
                "all_caps": 0,
                "lowercase": 0
            },
            "common_prefixes": [],
            "uses_brackets_rate": 0
        }

    # Casing distribution
    casing_total = sum(casing_counts.values())
    casing_dist = {
        "title_case": round(casing_counts.get("title_case", 0) / casing_total, 2) if casing_total else 0,
        "sentence_case": round(casing_counts.get("sentence_case", 0) / casing_total, 2) if casing_total else 0,
        "all_caps": round(casing_counts.get("all_caps", 0) / casing_total, 2) if casing_total else 0,
        "lowercase": round(casing_counts.get("lowercase", 0) / casing_total, 2) if casing_total else 0
    }

    return {
        "length_chars_range": [min(lengths), max(lengths)],
        "avg_word_count": round(sum(word_counts) / len(word_counts), 1),
        "casing_distribution": casing_dist,
        "common_prefixes": [p for p, _ in prefix_counts.most_common(5)],
        "uses_brackets_rate": round(brackets_count / total, 2) if total else 0
    }


# =============================================================================
# MECHANICS ANALYSIS
# =============================================================================

# Common contractions
CONTRACTIONS = [
    "I'm", "I'll", "I've", "I'd",
    "we're", "we'll", "we've", "we'd",
    "you're", "you'll", "you've", "you'd",
    "they're", "they'll", "they've", "they'd",
    "he's", "she's", "it's",
    "that's", "there's", "here's",
    "don't", "doesn't", "didn't",
    "can't", "couldn't", "wouldn't", "shouldn't",
    "won't", "isn't", "aren't", "wasn't", "weren't",
    "haven't", "hasn't", "hadn't",
    "let's", "what's", "who's"
]

CONTRACTION_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(c) for c in CONTRACTIONS) + r")\b",
    re.IGNORECASE
)


def analyze_mechanics(emails: List[Dict]) -> Dict:
    """
    Detect punctuation and mechanics patterns.

    Returns:
        {
            "uses_contractions": bool,
            "contraction_rate": float,
            "common_contractions": [str],
            "uses_em_dash": bool,
            "uses_semicolons": bool,
            "uses_ellipsis": bool,
            "exclamation_rate": float,
            "question_rate": float
        }
    """
    if not emails:
        return {
            "uses_contractions": False,
            "contraction_rate": 0,
            "common_contractions": [],
            "uses_em_dash": False,
            "uses_semicolons": False,
            "uses_ellipsis": False,
            "exclamation_rate": 0,
            "question_rate": 0
        }

    contraction_counts = Counter()
    emails_with_contractions = 0
    emails_with_em_dash = 0
    emails_with_semicolons = 0
    emails_with_ellipsis = 0
    exclamation_count = 0
    question_count = 0
    total_emails = 0

    for email in emails:
        body = _get_body(email)
        if not body:
            continue

        total_emails += 1

        # Count contractions
        contractions_found = CONTRACTION_PATTERN.findall(body)
        if contractions_found:
            emails_with_contractions += 1
            for c in contractions_found:
                contraction_counts[c.lower()] += 1

        # Check for em-dash (both -- and —)
        if '--' in body or '—' in body or '–' in body:
            emails_with_em_dash += 1

        # Check for semicolons
        if ';' in body:
            emails_with_semicolons += 1

        # Check for ellipsis
        if '...' in body or '…' in body:
            emails_with_ellipsis += 1

        # Count exclamations and questions
        exclamation_count += body.count('!')
        question_count += body.count('?')

    if total_emails == 0:
        return {
            "uses_contractions": False,
            "contraction_rate": 0,
            "common_contractions": [],
            "uses_em_dash": False,
            "uses_semicolons": False,
            "uses_ellipsis": False,
            "exclamation_rate": 0,
            "question_rate": 0
        }

    return {
        "uses_contractions": emails_with_contractions > total_emails * 0.3,
        "contraction_rate": round(emails_with_contractions / total_emails, 2),
        "common_contractions": [c for c, _ in contraction_counts.most_common(5)],
        "uses_em_dash": emails_with_em_dash > total_emails * 0.1,
        "uses_semicolons": emails_with_semicolons > total_emails * 0.1,
        "uses_ellipsis": emails_with_ellipsis > total_emails * 0.1,
        "exclamation_rate": round(exclamation_count / total_emails, 2),
        "question_rate": round(question_count / total_emails, 2)
    }


# =============================================================================
# SENIORITY DETECTION
# =============================================================================

EXECUTIVE_TITLES = [
    r'\bCEO\b', r'\bCFO\b', r'\bCTO\b', r'\bCOO\b', r'\bCMO\b', r'\bCIO\b',
    r'\bChief\s+\w+\s+Officer\b',
    r'\bVP\b', r'\bVice\s+President\b',
    r'\bPresident\b', r'\bDirector\b',
    r'\bSVP\b', r'\bEVP\b',
    r'\bGeneral\s+Manager\b', r'\bManaging\s+Director\b',
    r'\bHead\s+of\b', r'\bSenior\s+Director\b'
]

JUNIOR_INDICATORS = [
    r'\bIntern\b', r'\bJunior\b', r'\bAssociate\b',
    r'\bEntry[-\s]?Level\b', r'\bCoordinator\b',
    r'\bAssistant\b'
]

RECRUITING_KEYWORDS = [
    r'\binterview\b', r'\bcandidate\b', r'\bapplicant\b',
    r'\bposition\b', r'\bjob\b', r'\brole\b', r'\bopening\b',
    r'\bhiring\b', r'\brecruit\b'
]


def detect_recipient_seniority(email: Dict) -> str:
    """
    Detect recipient role from email patterns.

    Returns: One of ['executive', 'peer', 'report', 'external_client', 'candidate', 'unknown']
    """
    # Get relevant fields
    to_field = ""
    from_field = ""
    body = ""
    enrichment = {}

    if "original_data" in email:
        to_field = email["original_data"].get("to", "") or ""
        from_field = email["original_data"].get("from", "") or ""
        body = email["original_data"].get("body", "") or ""

    if "enrichment" in email:
        enrichment = email["enrichment"]

    # Check for recipient signatures (if available in enrichment)
    recipient_sigs = enrichment.get("recipient_signatures", [])
    if isinstance(recipient_sigs, list):
        sig_text = " ".join(recipient_sigs)
    else:
        sig_text = str(recipient_sigs) if recipient_sigs else ""

    combined_text = f"{to_field} {sig_text}"

    # Check for executive titles
    for pattern in EXECUTIVE_TITLES:
        if re.search(pattern, combined_text, re.IGNORECASE):
            return "executive"

    # Check for external (different domain)
    audience = enrichment.get("audience", "")
    if audience == "external":
        return "external_client"

    # Try to detect from domain mismatch
    if to_field and from_field:
        to_domain = re.search(r'@([\w.-]+)', to_field)
        from_domain = re.search(r'@([\w.-]+)', from_field)
        if to_domain and from_domain:
            if to_domain.group(1).lower() != from_domain.group(1).lower():
                return "external_client"

    # Check for recruiting context
    for pattern in RECRUITING_KEYWORDS:
        if re.search(pattern, body, re.IGNORECASE):
            return "candidate"

    # Check for junior indicators (might be a report)
    for pattern in JUNIOR_INDICATORS:
        if re.search(pattern, combined_text, re.IGNORECASE):
            return "report"

    # Default to peer for internal emails
    if audience == "internal" or (not audience and not to_field):
        return "peer"

    return "unknown"


# =============================================================================
# EMAIL TYPE INFERENCE
# =============================================================================

def infer_email_types(cluster: Dict, emails: List[Dict]) -> Dict:
    """
    Infer email type definitions from cluster patterns.

    Returns:
        {
            "detected_type": str,
            "confidence": float,
            "required_elements": [str],
            "typical_length": {"min": int, "max": int},
            "structure_pattern": str
        }
    """
    if not emails:
        return {
            "detected_type": "general",
            "confidence": 0.5,
            "required_elements": [],
            "typical_length": {"min": 100, "max": 300},
            "structure_pattern": "paragraph"
        }

    # Analyze cluster enrichment
    enrichment = cluster.get("enrichment_summary", {})
    recipient_types = enrichment.get("recipient_types", {})
    audiences = enrichment.get("audiences", {})

    # Analyze email content
    has_bullets = 0
    has_status_keywords = 0
    has_outreach_keywords = 0
    has_request_keywords = 0
    total_lengths = []

    status_keywords = ['update', 'status', 'progress', 'completed', 'blockers', 'next steps']
    outreach_keywords = ['reaching out', 'reach out', 'introduction', 'introduce myself', 'connect', 'opportunity']
    request_keywords = ['please', 'could you', 'can you', 'would you', 'need', 'request']

    for email in emails:
        body = _get_body(email).lower()
        subject = _get_subject(email).lower()

        if BULLET_PATTERN.search(_get_body(email)):
            has_bullets += 1

        for kw in status_keywords:
            if kw in body or kw in subject:
                has_status_keywords += 1
                break

        for kw in outreach_keywords:
            if kw in body:
                has_outreach_keywords += 1
                break

        for kw in request_keywords:
            if kw in body:
                has_request_keywords += 1
                break

        total_lengths.append(len(_get_body(email)))

    n = len(emails)
    bullet_rate = has_bullets / n if n else 0
    status_rate = has_status_keywords / n if n else 0
    outreach_rate = has_outreach_keywords / n if n else 0
    request_rate = has_request_keywords / n if n else 0

    # Determine type based on patterns
    if status_rate > 0.5 and bullet_rate > 0.4:
        return {
            "detected_type": "internal_status_update",
            "confidence": min(0.9, status_rate + bullet_rate * 0.3),
            "required_elements": ["status", "blockers", "next_steps", "timeline"],
            "typical_length": {"min": 120, "max": 300},
            "structure_pattern": "bullet_heavy"
        }

    if outreach_rate > 0.4 and audiences.get("external", 0) > 0.5:
        return {
            "detected_type": "cold_outreach",
            "confidence": min(0.85, outreach_rate + 0.2),
            "required_elements": ["hook", "credibility", "clear_ask", "easy_out"],
            "typical_length": {"min": 70, "max": 150},
            "structure_pattern": "concise"
        }

    if request_rate > 0.5:
        return {
            "detected_type": "request",
            "confidence": min(0.8, request_rate),
            "required_elements": ["context", "ask", "deadline"],
            "typical_length": {"min": 80, "max": 200},
            "structure_pattern": "paragraph"
        }

    # Default to general
    avg_len = sum(total_lengths) / len(total_lengths) if total_lengths else 200
    return {
        "detected_type": "general",
        "confidence": 0.6,
        "required_elements": ["context", "point", "close"],
        "typical_length": {"min": int(avg_len * 0.5), "max": int(avg_len * 1.5)},
        "structure_pattern": "paragraph"
    }


# =============================================================================
# V2 SCHEMA TEMPLATE
# =============================================================================

def get_v2_schema_template() -> Dict:
    """
    Return empty v2 schema template with all required sections.
    """
    return {
        "schema_version": "2.0",
        "profile_type": "email_persona",
        "persona_id": "",
        "cluster_name": "",
        "language": "en-US",
        "created_at": datetime.now().strftime("%Y-%m-%d"),

        "source_corpus": {
            "email_count": 0,
            "time_range": {"start": None, "end": None},
            "domains": [],
            "data_hygiene_status": "pii_redacted_signatures_removed"
        },

        "voice_fingerprint": {
            "formality": {
                "level": 5,
                "instruction": ""
            },
            "rhythm": {},
            "mechanics": {},
            "lexicon": {
                "signature_phrases": [],
                "common_transitions": [],
                "preferred_verbs": [],
                "banned_words_or_phrases": [],
                "jargon_level": "medium"
            },
            "tone_markers": {
                "warmth": {"level": 5, "instruction": ""},
                "authority": {"level": 5, "instruction": ""},
                "directness": {"level": 5, "instruction": ""}
            },
            "credibility_markers": {
                "uses_specifics_over_vague": True,
                "uses_numbers_when_available": True,
                "source_citation_style": "inline",
                "states_assumptions_explicitly": True
            }
        },

        "cognitive_load_preferences": {
            "bottom_line_up_front": True,
            "action_item_isolation": "inline",
            "information_density": "medium",
            "scannability_instruction": ""
        },

        "email_channel_rules": {
            "deliverability": {
                "avoid_spam_triggers": True,
                "max_links_per_email": 3
            },
            "mobile_readability": {
                "max_paragraph_lines_preference": 4,
                "prefers_scannable_formatting": True
            }
        },

        "subject_line_dna": {},
        "opening_dna": {},
        "body_dna": {
            "structure_preferences": {},
            "argumentation_style": {},
            "clarity_habits": {},
            "typical_length": {}
        },
        "cta_dna": {},
        "closing_dna": {},
        "threading_and_reply_dna": {},
        "relationship_calibration": {"recipient_segments": {}},

        "guardrails": {
            "structural_anti_patterns": [],
            "never_do": [],
            "sensitive_topics": {},
            "confidentiality": {}
        },

        "variation_controls": {
            "allowed_deviation": {},
            "signature_phrase_max_per_email": 1,
            "avoid_repetition_window_emails": 5
        },

        "email_types": {},

        "example_bank": {
            "usage_guidance": {
                "instruction": "Match rhythm, tone, and structural patterns.",
                "what_to_match": [],
                "what_to_adapt": [],
                "warning": "Do NOT copy examples verbatim."
            },
            "examples": []
        },

        "evaluation_rubric": {
            "voice_match_dimensions": [
                {"name": "tone_match", "scale": [1, 5]},
                {"name": "clarity_and_structure", "scale": [1, 5]},
                {"name": "ask_specificity", "scale": [1, 5]},
                {"name": "politeness_without_fluff", "scale": [1, 5]},
                {"name": "persona_distinctiveness", "scale": [1, 5]}
            ],
            "self_checklist": [
                "Did I state the purpose in the first 1-2 sentences?",
                "Is the ask explicit with owner and timeframe?",
                "Did I avoid banned phrases?",
                "Is the length within target range?",
                "Would I actually send this?"
            ]
        }
    }


# =============================================================================
# MASTER FUNCTION
# =============================================================================

def compute_deterministic_metrics(emails: List[Dict]) -> Dict:
    """
    Compute all deterministic metrics for v2 schema.
    Aggregates all analysis functions into a unified result.
    """
    return {
        "rhythm": analyze_rhythm(emails),
        "formatting": analyze_formatting(emails),
        "greeting_distribution": extract_greeting_distribution(emails),
        "closing_distribution": extract_closing_distribution(emails),
        "subject_line_patterns": analyze_subject_lines(emails),
        "mechanics": analyze_mechanics(emails)
    }


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

def detect_schema_version(batch: Dict) -> str:
    """
    Detect schema version from batch structure.

    Returns: "1.0" or "2.0"
    """
    # V2 has explicit schema_version
    if "schema_version" in batch:
        return batch["schema_version"]

    # V2 personas have voice_fingerprint
    personas = batch.get("new_personas", [])
    if personas:
        if "voice_fingerprint" in personas[0]:
            return "2.0"

    # Default to v1
    return "1.0"


def migrate_v1_to_v2(persona: Dict) -> Dict:
    """
    Migrate v1 persona to v2 structure.

    Maps old characteristics to new voice_fingerprint structure.
    Adds placeholder values for new fields.
    """
    chars = persona.get("characteristics", {})

    v2_persona = get_v2_schema_template()

    # Copy basic fields
    v2_persona["schema_version"] = "2.0"
    v2_persona["name"] = persona.get("name", "")
    v2_persona["description"] = persona.get("description", "")
    v2_persona["cluster_name"] = persona.get("name", "")

    # Map voice fingerprint
    v2_persona["voice_fingerprint"]["formality"] = {
        "level": chars.get("formality", 5),
        "instruction": ""  # Placeholder - needs LLM enrichment
    }

    # Map tone markers
    v2_persona["voice_fingerprint"]["tone_markers"] = {
        "warmth": {
            "level": chars.get("warmth", 5),
            "instruction": ""
        },
        "authority": {
            "level": chars.get("authority", 5),
            "instruction": ""
        },
        "directness": {
            "level": chars.get("directness", 5),
            "instruction": ""
        }
    }

    # Map mechanics
    v2_persona["voice_fingerprint"]["mechanics"] = {
        "uses_contractions": chars.get("uses_contractions", True),
        "contraction_rate": 0.5 if chars.get("uses_contractions", True) else 0
    }

    # Map opening/closing
    if chars.get("typical_greeting"):
        v2_persona["opening_dna"] = {
            "greeting_distribution": {chars["typical_greeting"]: 1.0},
            "primary_style": chars["typical_greeting"]
        }

    if chars.get("typical_closing"):
        v2_persona["closing_dna"] = {
            "sign_off_distribution": {chars["typical_closing"]: 1.0},
            "primary_style": chars["typical_closing"],
            "uses_signature_block": False
        }

    # Map formatting
    if chars.get("uses_bullets") is not None:
        v2_persona["body_dna"]["structure_preferences"] = {
            "uses_bullets_rate": 0.6 if chars.get("uses_bullets") else 0.1
        }

    # Placeholder guardrails
    v2_persona["guardrails"] = {
        "structural_anti_patterns": [],
        "never_do": [],
        "sensitive_topics": {},
        "confidentiality": {}
    }

    return v2_persona


# =============================================================================
# EXAMPLE BANK SELECTION
# =============================================================================

def select_example_bank(
    samples: List[Dict],
    limit: int = 5,
    min_confidence: float = 0.85
) -> List[Dict]:
    """
    Select top examples for the example_bank based on confidence scores.

    Args:
        samples: List of sample dicts with 'confidence' field
        limit: Maximum number of examples to select
        min_confidence: Minimum confidence threshold (default 0.85)

    Returns:
        List of selected samples sorted by confidence descending
    """
    if not samples:
        return []

    # Filter by confidence and sort
    eligible = [s for s in samples if s.get("confidence", 0) >= min_confidence]
    eligible.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return eligible[:limit]


if __name__ == "__main__":
    # Example usage
    sample_emails = [
        {
            "original_data": {
                "subject": "Quick update on project",
                "body": "Hi Team,\n\nHere's the update:\n- Item 1\n- Item 2\n\nBest,\nJohn"
            }
        }
    ]

    metrics = compute_deterministic_metrics(sample_emails)
    print(json.dumps(metrics, indent=2))
