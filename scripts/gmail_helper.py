import os
import base64
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from scripts.config import SCOPES, TOKEN_FILE, DRY_RUN


def get_gmail_service():
    """Load session token, refresh if expired, and return Gmail API service."""
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"Token file '{TOKEN_FILE}' not found. Please run 'python auth_setup.py' first."
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        print("[INFO] Gmail OAuth token expired. Refreshing token...")
        creds.refresh(Request())
        with open(TOKEN_FILE, 'w', encoding='utf-8') as token_out:
            token_out.write(creds.to_json())

    if not creds or not creds.valid:
        raise ValueError("Invalid credentials. Please re-run auth_setup.py.")

    return build('gmail', 'v1', credentials=creds)


def extract_header_value(headers, name):
    """Retrieve header value by case-insensitive name match."""
    for header in headers:
        if header.get('name', '').lower() == name.lower():
            return header.get('value', '')
    return ''


def parse_email_parts(payload):
    """Recursively extract raw HTML or plain text body from email payload."""
    html_body = None
    text_body = None

    def _walk_parts(part):
        nonlocal html_body, text_body
        mime_type = part.get('mimeType', '')
        body = part.get('body', {})
        data = body.get('data')

        if data:
            decoded_bytes = base64.urlsafe_b64decode(data.encode('UTF-8'))
            decoded_content = decoded_bytes.decode('utf-8', errors='replace')
            if mime_type == 'text/html' and not html_body:
                html_body = decoded_content
            elif mime_type == 'text/plain' and not text_body:
                text_body = decoded_content

        parts = part.get('parts', [])
        for sub_part in parts:
            _walk_parts(sub_part)

    _walk_parts(payload)
    return html_body or text_body or "<p>No content extracted from email.</p>"


def parse_email_date(date_str):
    """Parse RFC 2822 date header into datetime object."""
    if date_str:
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def mark_email_as_read(service, msg_id):
    """Remove UNREAD label from processed email."""
    if DRY_RUN:
        print(f"[DRY-RUN] Would mark email ID '{msg_id}' as READ.")
        return

    try:
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        print(f"[SUCCESS] Marked email ID '{msg_id}' as READ.")
    except Exception as err:
        print(f"[WARNING] Could not mark email ID '{msg_id}' as READ: {err}")
