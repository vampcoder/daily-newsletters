import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.gmail_helper import get_gmail_service

def main():
    service = get_gmail_service()
    
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    
    print("Available custom labels:")
    for label in labels:
        if label.get('type') == 'user':
            print(f"- Name: {label.get('name')} | ID: {label.get('id')}")

if __name__ == '__main__':
    main()
