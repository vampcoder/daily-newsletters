import re

from scripts.config import PROMO_KEYWORDS, SENDER_SUBJECT_FILTERS


def should_filter_by_sender_subject(sender, subject):
    """
    Check if the email should be skipped based on SENDER_SUBJECT_FILTERS.
    Supports allowlists (subject must contain at least one) and blocklists (subject must not contain any).
    """
    sender_lower = sender.lower()
    subject_lower = subject.lower()
    
    for filter_sender, rules in SENDER_SUBJECT_FILTERS.items():
        if filter_sender.lower() in sender_lower:
            # Check blocklist first
            if 'block' in rules:
                if any(block.lower() in subject_lower for block in rules['block']):
                    return True
            # Check allowlist
            if 'allow' in rules:
                if not any(allow.lower() in subject_lower for allow in rules['allow']):
                    return True
    return False


def is_promotional_email(subject, sender, text_body):
    """Check if email is marketing spam, welcome email, discount blast, or announcement."""
    content_sample = f"{subject} {sender} {text_body[:500]}".lower()
    for pattern in PROMO_KEYWORDS:
        if re.search(pattern, content_sample):
            return True
    return False
