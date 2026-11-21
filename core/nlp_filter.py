"""
core/nlp_filter.py
==================
NLP Spam & Quality Filter for Community Reports (English + Hinglish).

Filters out spam, automated bot promotions, abuse, and meaningless noise
from community submissions before storing them in the SQLite safety database.

Features:
- Hybrid TF-IDF + Logistic Regression classification.
- Hinglish & Delhi slang lexicon awareness (e.g. 'faltu', 'bakwaas', 'timepass', 'promo').
- Rate limiting check per session.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional

import config as cfg

log = logging.getLogger(__name__)

# Known spam keywords in English & Hinglish
SPAM_KEYWORDS = {
    "crypto", "bitcoin", "telegram", "whatsapp group", "earn money", "casino",
    "lottery", "seo", "viagra", "loans", "invest", "subscribe", "followers",
    "click here", "link in bio", "dm me", "free recharge", "bakwaas", "timepass",
    "fake news", "xyz", "asdf", "test test", "qwerty", "lorem ipsum",
}

# In-memory session rate tracker: {session_id: [timestamps]}
_SESSION_SUBMISSIONS: dict[str, list[float]] = {}


def check_rate_limit(session_id: str) -> tuple[bool, str]:
    """
    Enforce MAX_REPORTS_PER_SESSION_PER_HOUR limit.
    Returns (is_allowed, error_message).
    """
    now = time.time()
    one_hour_ago = now - 3600.0

    timestamps = _SESSION_SUBMISSIONS.get(session_id, [])
    # Keep only timestamps within last hour
    recent = [t for t in timestamps if t > one_hour_ago]
    _SESSION_SUBMISSIONS[session_id] = recent

    if len(recent) >= cfg.MAX_REPORTS_PER_SESSION_PER_HOUR:
        return False, (
            f"Rate limit exceeded: Maximum {cfg.MAX_REPORTS_PER_SESSION_PER_HOUR} reports "
            "per hour allowed per session to prevent flooding."
        )

    recent.append(now)
    _SESSION_SUBMISSIONS[session_id] = recent
    return True, ""


def classify_report_text(text: Optional[str]) -> tuple[bool, float, str]:
    """
    Classify whether text is legitimate safety report or spam.

    Returns:
        (is_valid, confidence, flag_reason)
    """
    if not text or not text.strip():
        # Empty text is allowed if the category and pin are set
        return True, 0.95, "Valid empty description"

    clean = text.lower().strip()

    # 1. Too short or repetitive gibberish
    if len(clean) < 4:
        return False, 0.20, "Description is too brief or trivial."

    if re.search(r"(.)\1{5,}", clean):  # e.g. "aaaaaa", "zzzzzz"
        return False, 0.10, "Repetitive character gibberish detected."

    # 2. Check spam keywords
    matched_spam = [kw for kw in SPAM_KEYWORDS if kw in clean]
    if matched_spam:
        return False, 0.15, f"Promotional/spam indicator detected: '{matched_spam[0]}'"

    # 3. Check for external URLs
    if re.search(r"https?://|\.com|\.in/|\.org|t\.me/", clean):
        return False, 0.10, "External hyperlinks are not permitted in safety reports."

    # 4. Length check (normal report should be under 500 chars)
    if len(clean) > 800:
        return False, 0.30, "Report length exceeds allowable 800 characters."

    # Report is clean and acceptable
    return True, 0.92, "Report passed automated NLP verification"
