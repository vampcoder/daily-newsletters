#!/usr/bin/env python3
"""
reclassify_quarantined.py - Re-check emails quarantined under 'newsletter-spam' with the
current LLM model/prompt and restore (un-quarantine) any that now deserve the Newsletter
label. Run this after changing classification rules or the model.

Usage:
  python tools/reclassify_quarantined.py                  # real run (restores YES verdicts)
  DRY_RUN=true python tools/reclassify_quarantined.py     # preview only, no label changes
"""

import sys
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from scripts.config import DRY_RUN, NEWSLETTER_SPAM_LABEL, NEWSLETTER_LABEL_NAME, LLM_MODEL
from scripts.gmail_helper import (
    get_gmail_service,
    get_or_create_label,
    update_email_labels,
    extract_header_value,
    parse_email_parts,
)
from scripts.llm_curator import classify_newsletter_with_llm

LLM_MAX_WORKERS = int(os.getenv('LLM_MAX_WORKERS', '8'))


def _verdict(row):
    """LLM verdict for one quarantined email."""
    if row.get('error'):
        return 'ERR', None, f"fetch error: {row['error']}"
    try:
        should_pub, score, reason = classify_newsletter_with_llm(
            row['subject'], row['sender'], row['body']
        )
        return ('YES' if should_pub else 'NO'), score, reason
    except Exception as err:
        return 'ERR', None, f"LLM error: {err}"


def main():
    print("=" * 60)
    print("      Reclassify Quarantined Emails (newsletter-spam)      ")
    print("=" * 60)
    print(f"[CONFIG] Model: {LLM_MODEL}")
    if DRY_RUN:
        print("[CONFIG] DRY_RUN: label changes will be simulated, not applied")

    service = get_gmail_service()
    spam_label_id = get_or_create_label(service, NEWSLETTER_SPAM_LABEL)
    newsletter_label_id = get_or_create_label(service, NEWSLETTER_LABEL_NAME)

    # Fetch all quarantined emails (paginated)
    rows = []
    page_token = None
    while True:
        kwargs = {'userId': 'me', 'q': f'label:"{NEWSLETTER_SPAM_LABEL}"', 'maxResults': 500}
        if page_token:
            kwargs['pageToken'] = page_token
        results = service.users().messages().list(**kwargs).execute()
        messages = results.get('messages', [])
        for i, msg_summary in enumerate(messages, 1):
            msg_id = msg_summary['id']
            try:
                msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
                headers = msg.get('payload', {}).get('headers', [])
                rows.append({
                    'id': msg_id,
                    'subject': extract_header_value(headers, 'Subject') or 'Untitled',
                    'sender': extract_header_value(headers, 'From') or 'Unknown',
                    'body': parse_email_parts(msg.get('payload', {})),
                })
            except Exception as err:
                rows.append({'id': msg_id, 'subject': '(fetch failed)', 'sender': '(unknown)',
                             'body': '', 'error': str(err)})
            if i % 100 == 0:
                print(f"[INFO] Fetched {i}/{len(messages)} quarantined emails.", flush=True)
        page_token = results.get('nextPageToken')
        if not page_token:
            break

    if not rows:
        print("[INFO] No quarantined emails found.")
        return

    print(f"[INFO] Reclassifying {len(rows)} quarantined email(s) with LLM "
          f"({LLM_MODEL}, {LLM_MAX_WORKERS} workers)...", flush=True)

    results = {}
    with ThreadPoolExecutor(max_workers=LLM_MAX_WORKERS) as pool:
        futures = {pool.submit(_verdict, row): row['id'] for row in rows}
        done = 0
        for future in as_completed(futures):
            msg_id = futures[future]
            try:
                results[msg_id] = future.result()
            except Exception as err:
                results[msg_id] = ('ERR', None, f"unexpected error: {err}")
            done += 1
            if done % 50 == 0:
                print(f"[INFO] Classified {done}/{len(rows)}.", flush=True)

    restored, kept, errors = [], [], []
    for row in rows:
        verdict, score, reason = results.get(row['id'], ('ERR', None, 'not classified'))
        if verdict == 'YES':
            update_email_labels(
                service, row['id'],
                add_labels=[newsletter_label_id],
                remove_labels=[spam_label_id]
            )
            restored.append((row, reason))
        elif verdict == 'NO':
            kept.append(row)
        else:
            errors.append((row, reason))

    print()
    print("=" * 70)
    print(f"RESTORED to '{NEWSLETTER_LABEL_NAME}' ({len(restored)}):")
    for row, reason in restored:
        print(f"  [YES] {row['subject'][:75]} | {row['sender'][:45]}")
        print(f"        → {reason[:140]}")
    print(f"KEPT quarantined ({len(kept)}):")
    for row in kept:
        print(f"  [NO]  {row['subject'][:75]} | {row['sender'][:45]}")
    if errors:
        print(f"UNCLASSIFIED / ERRORS ({len(errors)}):")
        for row, reason in errors:
            print(f"  [ERR] {row['subject'][:75]} | {row['sender'][:45]} | {reason[:100]}")
    print("=" * 70)
    print(f"SUMMARY: {len(rows)} quarantined | RESTORED: {len(restored)} | "
          f"KEPT: {len(kept)} | ERR: {len(errors)}")


if __name__ == '__main__':
    main()
