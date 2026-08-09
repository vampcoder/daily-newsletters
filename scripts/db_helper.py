import os
import json
from pathlib import Path

from scripts.config import PROCESSED_EMAILS_FILE


def load_processed_email_ids():
    """Load previously processed Gmail message IDs to prevent duplicate posts."""
    if PROCESSED_EMAILS_FILE.exists():
        try:
            return set(json.loads(PROCESSED_EMAILS_FILE.read_text(encoding='utf-8')))
        except Exception:
            pass
    return set()


def save_processed_email_id(msg_id):
    """Save processed Gmail message ID to persistent store."""
    processed = load_processed_email_ids()
    processed.add(msg_id)
    try:
        PROCESSED_EMAILS_FILE.write_text(json.dumps(sorted(list(processed)), indent=2), encoding='utf-8')
    except Exception as err:
        print(f"[WARNING] Could not save processed email ID '{msg_id}': {err}")
