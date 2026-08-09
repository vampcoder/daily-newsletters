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
    
    idx = raw_html.find("one in five compl")
    if idx != -1:
        print("=== FOUND IN RAW HTML ===")
        print(raw_html[idx-100:idx+400])
    else:
        print("Not found in raw HTML.")

if __name__ == '__main__':
    main()
