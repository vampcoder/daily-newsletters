import sys
import re
from pathlib import Path
from bs4 import BeautifulSoup
import markdownify

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.gmail_helper import get_gmail_service, parse_email_parts
from scripts.content_parser import clean_html

def main():
    service = get_gmail_service()
    msg_id = '19fdfd4b99454293'
    
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = msg.get('payload', {})
    raw_html = parse_email_parts(payload)
    
    soup = clean_html(raw_html)
    raw_markdown = markdownify.markdownify(
        str(soup),
        heading_style="ATX",
        strip=['script', 'style', 'table', 'tr', 'td', 'tbody', 'thead']
    ).strip()
    
    idx = raw_markdown.find("one in five")
    if idx != -1:
        print("=== FOUND IN RAW MARKDOWN ===")
        print(raw_markdown[idx-100:idx+800])
    else:
        print("Not found in raw markdown.")

if __name__ == '__main__':
    main()
