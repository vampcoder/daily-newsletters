import sys
import re
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.gmail_helper import get_gmail_service, parse_email_parts
from scripts.content_parser import build_jekyll_markdown

def main():
    service = get_gmail_service()
    msg_id = '19fdfd4b99454293'
    
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = msg.get('payload', {})
    raw_html = parse_email_parts(payload)
    
    headers = payload.get('headers', [])
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'No Sender')
    
    from datetime import datetime, timezone
    email_dt = datetime.now(timezone.utc)
    
    print("Running build_jekyll_markdown with LLM polishing enabled...")
    markdown_doc, is_summary, excerpt, img_url = build_jekyll_markdown(
        subject, sender, email_dt, raw_html, []
    )
    
    print("\n=== GENERATED MARKDOWN DOC (Last 1000 chars) ===")
    print(markdown_doc[-1000:])

if __name__ == '__main__':
    main()
