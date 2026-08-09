import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.gmail_helper import get_gmail_service

def main():
    service = get_gmail_service()
    
    # Search label:newsletter for "IRDAI"
    q = 'IRDAI'
    print(f"Searching Gmail for: {q}...")
    results = service.users().messages().list(userId='me', q=q).execute()
    messages = results.get('messages', [])
    
    if not messages:
        print("No messages found matching IRDAI.")
        return
        
    print(f"Found {len(messages)} matching email(s):")
    for msg_summary in messages:
        msg_id = msg_summary['id']
        msg = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
        
        headers = msg.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'No Sender')
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'No Date')
        
        labels = msg.get('labelIds', [])
        print(f"- ID: {msg_id}")
        print(f"  Subject: {subject}")
        print(f"  From: {sender}")
        print(f"  Date: {date}")
        print(f"  Labels: {labels}")

if __name__ == '__main__':
    main()
