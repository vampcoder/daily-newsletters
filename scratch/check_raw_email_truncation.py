import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.gmail_helper import get_gmail_service, parse_email_parts

def main():
    service = get_gmail_service()
    msg_id = '19fdfd4b99454293'
    
    msg = service.users().messages().get(
        userId='me',
        id=msg_id,
        format='full'
    ).execute()
    
    payload = msg.get('payload', {})
    raw_html = parse_email_parts(payload)
    
    print(f"Raw body content length: {len(raw_html)} characters.")
    print("End of raw body content:")
    print(raw_html[-500:])

if __name__ == '__main__':
    main()
