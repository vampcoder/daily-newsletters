import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.config import GITHUB_REPO, POSTS_DIR, DRY_RUN
from scripts.gmail_helper import get_gmail_service, parse_email_parts, parse_email_date, extract_header_value
from scripts.github_helper import get_github_repo, publish_to_github
from scripts.content_parser import get_existing_categories, build_jekyll_markdown, slugify

def reprocess_email_by_id(msg_id):
    print(f"[INFO] Reprocessing email ID: {msg_id}")
    service = get_gmail_service()
    
    try:
        repo = get_github_repo()
        print(f"[INFO] Connected to GitHub repository: {repo.full_name}")
    except Exception as err:
        print(f"[WARNING] GitHub repository client initialization failed: {err}")
        repo = None

    try:
        msg = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()

        payload = msg.get('payload', {})
        headers = payload.get('headers', [])

        subject = extract_header_value(headers, 'Subject') or 'Untitled Newsletter'
        sender = extract_header_value(headers, 'From') or 'Newsletter'
        date_header = extract_header_value(headers, 'Date')
        email_dt = parse_email_date(date_header)

        raw_html = parse_email_parts(payload)
        existing_categories = get_existing_categories()

        print(f"[INFO] Processing newsletter: '{subject}' ({msg_id})")

        markdown_doc, is_summary, excerpt, img_url = build_jekyll_markdown(
            subject, sender, email_dt, raw_html, existing_categories
        )

        date_prefix = email_dt.strftime('%Y-%m-%d')
        subject_slug = slugify(subject)
        filename = f"{date_prefix}-{subject_slug}.md"

        print(f"[INFO] Publishing updated post to GitHub: {filename}")
        publish_to_github(repo, filename, markdown_doc, subject)
        print("[SUCCESS] Reprocessing complete!")

    except Exception as err:
        print(f"[ERROR] Failed to reprocess email ID '{msg_id}': {err}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        target_id = sys.argv[1]
    else:
        target_id = '19fdfd4b99454293' # Default to the IRDAI email
    reprocess_email_by_id(target_id)
