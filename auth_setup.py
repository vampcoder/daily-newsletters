#!/usr/bin/env python3
"""
auth_setup.py - One-time local setup script to authenticate with Gmail API.

This script initiates an interactive Google OAuth2 authentication flow in your local
web browser. Upon completion, it saves the authorization token into `token.json`,
which the headless Docker application uses for automated background execution.
"""

import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = Path('credentials.json')
TOKEN_FILE = Path('token.json')


def main():
    print("=" * 60)
    print("      Gmail Newsletter Pipeline - OAuth Setup Utility      ")
    print("=" * 60)

    if not CREDENTIALS_FILE.exists():
        print(f"\n[ERROR] Credentials file '{CREDENTIALS_FILE}' not found!")
        print("Please ensure credentials.json is present in the project directory.")
        sys.exit(1)

    print(f"\n[INFO] Found '{CREDENTIALS_FILE}'. Launching OAuth authorization flow...")
    print("[INFO] Opening local browser server for authorization...")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE), SCOPES
        )
        creds = flow.run_local_server(port=0, open_browser=True)

        with open(TOKEN_FILE, 'w', encoding='utf-8') as token_file:
            token_file.write(creds.to_json())

        print("\n[SUCCESS] Authentication successful!")
        print(f"[SUCCESS] Token successfully saved to '{TOKEN_FILE}'.")

    except Exception as exc:
        print(f"\n[ERROR] Authentication flow failed: {exc}")
        sys.exit(1)


if __name__ == '__main__':
    main()
