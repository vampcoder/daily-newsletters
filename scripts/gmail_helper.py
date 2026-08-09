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


def html_to_text(html):
    """Convert raw email HTML to clean plain text for LLM previews (tags stripped, whitespace collapsed)."""
    if not html:
        return ''
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    for element in soup(['script', 'style', 'head', 'meta', 'link']):
        element.decompose()
    text = soup.get_text(separator=' ')
    return ' '.join(text.split())


def get_or_create_label(service, label_name):
    """Return the Gmail label ID for label_name, creating the label if it doesn't exist."""
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    for label in labels:
        if label.get('name', '').lower() == label_name.lower():
            return label['id']

    if DRY_RUN:
        print(f"[DRY-RUN] Would create Gmail label '{label_name}'.")
        return f"dry-run:{label_name}"

    created = service.users().labels().create(
        userId='me',
        body={
            'name': label_name,
            'messageListVisibility': 'show',
            'labelListVisibility': 'labelShow'
        }
    ).execute()
    print(f"[INFO] Created new Gmail label '{label_name}'.")
    return created['id']


def update_email_labels(service, msg_id, add_labels=None, remove_labels=None):
    """Add and/or remove Gmail labels on a message. Respects DRY_RUN."""
    body = {}
    if add_labels:
        body['addLabelIds'] = list(add_labels)
    if remove_labels:
        body['removeLabelIds'] = list(remove_labels)
    if not body:
        return

    if DRY_RUN:
        print(f"[DRY-RUN] Would modify labels on email '{msg_id}': "
              f"add={body.get('addLabelIds')} remove={body.get('removeLabelIds')}")
        return

    service.users().messages().modify(userId='me', id=msg_id, body=body).execute()
    print(f"[SUCCESS] Updated labels on email '{msg_id}': "
          f"add={body.get('addLabelIds')} remove={body.get('removeLabelIds')}")


def reconcile_quarantine_labels(service, spam_label_id, newsletter_label_id):
    """Drop the newsletter label from any message carrying both labels.

    Safety net for when a Gmail filter is edited and 'Also apply filter to matching
    conversations' re-adds the Newsletter label to already-quarantined emails.
    Returns the number of messages fixed. Respects DRY_RUN.
    """
    fixed = 0
    page_token = None
    while True:
        kwargs = {'userId': 'me', 'q': 'label:newsletter label:"newsletter-spam"', 'maxResults': 500}
        if page_token:
            kwargs['pageToken'] = page_token
        results = service.users().messages().list(**kwargs).execute()
        messages = results.get('messages', [])
        for msg_summary in messages:
            msg_id = msg_summary['id']
            try:
                msg = service.users().messages().get(userId='me', id=msg_id, format='metadata').execute()
            except Exception as err:
                print(f"[WARNING] Could not inspect email '{msg_id}' during reconcile: {err}")
                continue
            label_ids = set(msg.get('labelIds', []))
            if newsletter_label_id in label_ids and spam_label_id in label_ids:
                update_email_labels(service, msg_id, remove_labels=[newsletter_label_id])
                fixed += 1
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    return fixed


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
