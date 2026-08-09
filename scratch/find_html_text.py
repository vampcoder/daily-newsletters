import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.gmail_helper import get_gmail_service, parse_email_parts

def main():
    service = get_gmail_service()
    msg_id = '19fdfd4b99454293'
    
    msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = msg.get('payload', {})
    raw_html = parse_email_parts(payload)
    
    # Print the last 2000 characters of raw HTML text content (not tags)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw_html, 'html.parser')
    text = soup.get_text()
    
    print(f"Total plain text length: {len(text)} characters.")
    print("=== LAST 1500 CHARACTERS OF PLAIN TEXT ===")
    print(text[-1500:])

if __name__ == '__main__':
    main()
