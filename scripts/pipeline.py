import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# Import configurations
from scripts.config import (
    DRY_RUN,
    ENABLE_LLM_CURATION,
    LLM_API_KEY,
    LLM_MODEL,
    MIN_RELEVANCE_SCORE,
    NEWSLETTER_SPAM_LABEL,
    NEWSLETTER_LABEL_NAME
)

try:
    import litellm
except ImportError:
    litellm = None

# Import Gmail helpers
from scripts.gmail_helper import (
    get_gmail_service,
    extract_header_value,
    parse_email_parts,
    parse_email_date,
    mark_email_as_read,
    get_or_create_label,
    update_email_labels,
    reconcile_quarantine_labels
)

# Import GitHub helpers
from scripts.github_helper import get_github_repo, publish_to_github

# Import LLM curation calls
from scripts.llm_curator import curate_newsletter_with_llm, classify_newsletter_with_llm

# Import parsing & formatting helpers
from scripts.content_parser import (
    get_existing_categories,
    split_the_batch_email,
    build_jekyll_markdown,
    slugify
)

# Import filters
from scripts.filters import should_filter_by_sender_subject, is_promotional_email

# Import deduplication cache DB helpers
from scripts.db_helper import load_processed_email_ids, save_processed_email_id


def process_inbox():
    """Main execution job to query, filter, LLM curate/polish, convert, and publish newsletters."""
    print(f"\n[{datetime.now().isoformat()}] Starting newsletter processing run...")

    try:
        service = get_gmail_service()
    except Exception as err:
        print(f"[ERROR] Failed to initialize Gmail service: {err}")
        return

    repo = None
    if not DRY_RUN:
        try:
            repo = get_github_repo()
            print(f"[INFO] Connected to GitHub repository: {repo.full_name}")
        except Exception as err:
            print(f"[WARNING] GitHub repository client initialization failed: {err}")
            print("[INFO] Running in local file save mode.")

    try:
        existing_categories = get_existing_categories()
        print(f"[INFO] Found {len(existing_categories)} existing categories: {existing_categories}")

        processed_ids = load_processed_email_ids()
        print(f"[INFO] Loaded {len(processed_ids)} previously processed email ID(s).")

        # Query all emails with label:newsletter (both read and unread) with pagination
        messages = []
        page_token = None
        while True:
            kwargs = {'userId': 'me', 'q': 'label:newsletter -label:"newsletter-spam"', 'maxResults': 500}
            if page_token:
                kwargs['pageToken'] = page_token
            results = service.users().messages().list(**kwargs).execute()
            messages.extend(results.get('messages', []))
            page_token = results.get('nextPageToken')
            if not page_token:
                break

        if not messages:
            print("[INFO] No newsletter emails found matching 'label:newsletter'.")
            return

        unfetched_messages = [m for m in messages if m['id'] not in processed_ids]
        print(f"[INFO] Found {len(messages)} total email(s) in 'label:newsletter' ({len(unfetched_messages)} un-fetched).")

        for msg_summary in unfetched_messages:
            msg_id = msg_summary['id']
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

                # Subject-based sender filtering
                if should_filter_by_sender_subject(sender, subject):
                    print(f"[SKIP] Subject-based sender filtering skipped: '{subject}' from '{sender}' ({msg_id})")
                    mark_email_as_read(service, msg_id)
                    save_processed_email_id(msg_id)
                    continue

                # Rule-based Pre-Filter
                if is_promotional_email(subject, sender, raw_html):
                    print(f"[SKIP] Pre-filter promotional email skipped: '{subject}' ({msg_id})")
                    mark_email_as_read(service, msg_id)
                    save_processed_email_id(msg_id)
                    continue

                # Stage 1: LLM Curation Gate
                if ENABLE_LLM_CURATION and LLM_API_KEY and litellm:
                    should_pub, score, reason = curate_newsletter_with_llm(subject, sender, raw_html)
                    print(f"[LLM-GATE] Score: {score}/10 | Publish: {should_pub} | Rationale: {reason}")
                    if not should_pub or score < MIN_RELEVANCE_SCORE:
                        print(f"[SKIP] LLM Curation filtered out low relevance email: '{subject}'")
                        mark_email_as_read(service, msg_id)
                        save_processed_email_id(msg_id)
                        continue

                print(f"[INFO] Processing newsletter: '{subject}' ({msg_id})")

                # Multi-tile parsing for deeplearning.ai
                posts_to_process = []
                if 'deeplearning.ai' in sender.lower():
                    posts_to_process = split_the_batch_email(subject, raw_html)
                else:
                    posts_to_process = [{'title': subject, 'html': raw_html}]

                for post in posts_to_process:
                    post_title = post['title']
                    post_html = post['html']

                    markdown_doc, is_summary, excerpt, img_url = build_jekyll_markdown(
                        post_title, sender, email_dt, post_html, existing_categories
                    )

                    date_prefix = email_dt.strftime('%Y-%m-%d')
                    subject_slug = slugify(post_title)
                    filename = f"{date_prefix}-{subject_slug}.md"

                    publish_to_github(repo, filename, markdown_doc, post_title)
                
                mark_email_as_read(service, msg_id)
                save_processed_email_id(msg_id)

            except Exception as item_err:
                print(f"[ERROR] Failed to process email ID '{msg_id}': {item_err}")

    except Exception as batch_err:
        print(f"[ERROR] Batch execution error: {batch_err}")


# ---------------------------------------------------------------------------
# Report-only classification workflow (python main.py --classify)
# ---------------------------------------------------------------------------

CLASSIFY_REPORT_FILE = os.getenv('CLASSIFY_REPORT_FILE', 'classification_report.txt')
LLM_MAX_WORKERS = int(os.getenv('LLM_MAX_WORKERS', '8'))


def _fetch_newsletter_messages(service):
    """Fetch all messages under label:newsletter (paginated). Returns list of row dicts."""
    messages = []
    page_token = None
    while True:
        kwargs = {'userId': 'me', 'q': 'label:newsletter', 'maxResults': 500}
        if page_token:
            kwargs['pageToken'] = page_token
        results = service.users().messages().list(**kwargs).execute()
        messages.extend(results.get('messages', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break

    rows = []
    for i, msg_summary in enumerate(messages, 1):
        msg_id = msg_summary['id']
        try:
            msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            payload = msg.get('payload', {})
            headers = payload.get('headers', [])
            subject = extract_header_value(headers, 'Subject') or 'Untitled Newsletter'
            sender = extract_header_value(headers, 'From') or 'Newsletter'
            body = parse_email_parts(payload)
            rows.append({'id': msg_id, 'subject': subject, 'sender': sender, 'body': body})
        except Exception as err:
            rows.append({'id': msg_id, 'subject': '(fetch failed)', 'sender': '(unknown)',
                         'body': '', 'error': str(err)})
        if i % 100 == 0:
            print(f"[INFO] Fetched {i}/{len(messages)} emails from 'label:newsletter'.", flush=True)
    return rows


def _classify_row(row):
    """LLM verdict for one email. Rule-based filters are computed as context, not a gate."""
    if row.get('error'):
        return 'ERR', None, f"fetch error: {row['error']}"

    subject, sender, body = row['subject'], row['sender'], row['body']

    rule_notes = []
    if should_filter_by_sender_subject(sender, subject):
        rule_notes.append('sender-subject-rule')
    if is_promotional_email(subject, sender, body):
        rule_notes.append('promo-rule')

    try:
        should_pub, score, reason = classify_newsletter_with_llm(subject, sender, body)
        verdict = 'YES' if should_pub else 'NO'
    except Exception as err:
        return 'ERR', None, f"LLM error: {err}"

    if rule_notes:
        reason = f"[{' + '.join(rule_notes)}] {reason}"
    return verdict, score, reason


def classify_inbox(apply_labels=False):
    """Classification workflow: fetch every label:newsletter email, let the LLM decide
    newsletter vs spam, and print a plain YES/NO report.

    Does NOT publish, mark emails as read, or touch the dedup store.
    With apply_labels=True, NO-verdict emails get the '{NEWSLETTER_SPAM_LABEL}' label and
    the '{NEWSLETTER_LABEL_NAME}' label is removed (respects DRY_RUN).
    """
    print(f"\n[{datetime.now().isoformat()}] Starting newsletter classification run...")

    service = get_gmail_service()

    spam_label_id = None
    newsletter_label_id = None
    if apply_labels:
        spam_label_id = get_or_create_label(service, NEWSLETTER_SPAM_LABEL)
        newsletter_label_id = get_or_create_label(service, NEWSLETTER_LABEL_NAME)
        print(f"[INFO] Quarantine labels enabled: NO verdicts will be labeled "
              f"'{NEWSLETTER_SPAM_LABEL}' and unlabeled from '{NEWSLETTER_LABEL_NAME}'.")
        if DRY_RUN:
            print("[INFO] DRY_RUN is enabled — label changes will be simulated, not applied.")

        # Safety net: if 'Also apply filter to matching conversations' ever re-adds
        # the Newsletter label to quarantined emails, drop it before classifying.
        reconciled = reconcile_quarantine_labels(service, spam_label_id, newsletter_label_id)
        if reconciled:
            print(f"[INFO] Reconcile: removed '{NEWSLETTER_LABEL_NAME}' from {reconciled} "
                  f"already-quarantined email(s).")

    rows = _fetch_newsletter_messages(service)
    if not rows:
        print("[INFO] No newsletter emails found matching 'label:newsletter'.")
        return
    print(f"[INFO] Classifying {len(rows)} email(s) with LLM ({LLM_MODEL}, {LLM_MAX_WORKERS} workers)...")

    results = {}
    with ThreadPoolExecutor(max_workers=LLM_MAX_WORKERS) as pool:
        futures = {pool.submit(_classify_row, row): row['id'] for row in rows}
        done = 0
        for future in as_completed(futures):
            msg_id = futures[future]
            try:
                results[msg_id] = future.result()
            except Exception as err:
                results[msg_id] = ('ERR', None, f"unexpected error: {err}")
            done += 1
            if done % 100 == 0:
                print(f"[INFO] Classified {done}/{len(rows)}.", flush=True)

    labeled_count = 0
    if apply_labels:
        for row in rows:
            verdict = results.get(row['id'], ('ERR', None, ''))[0]
            if verdict != 'NO':
                continue
            update_email_labels(
                service,
                row['id'],
                add_labels=[spam_label_id],
                remove_labels=[newsletter_label_id]
            )
            labeled_count += 1
        print(f"[INFO] Quarantined {labeled_count} NO-verdict email(s) under "
              f"'{NEWSLETTER_SPAM_LABEL}'.")

    report_lines = []
    report_lines.append("CLASSIFICATION REPORT — label:newsletter -label:\"newsletter-spam\" (LLM verdict)")
    report_lines.append("=" * 100)
    for row in rows:
        verdict, score, reason = results.get(row['id'], ('ERR', None, 'not classified'))
        score_str = f"{score}/10" if score is not None else "---"
        report_lines.append(
            f"[{verdict}] {score_str} | {row['sender']} | {row['subject']} | {reason}"
        )

    verdicts = [r[0] for r in results.values()]
    yes_count = verdicts.count('YES')
    no_count = verdicts.count('NO')
    err_count = verdicts.count('ERR')
    report_lines.append("=" * 100)
    report_lines.append(
        f"SUMMARY: {len(rows)} emails | YES (newsletter): {yes_count} | NO (spam): {no_count} | ERR: {err_count}"
        + (f" | LABELED (quarantined): {labeled_count}" if apply_labels else "")
    )

    report = "\n".join(report_lines)
    print("\n" + report)

    try:
        Path(CLASSIFY_REPORT_FILE).write_text(report + "\n", encoding='utf-8')
        print(f"[INFO] Report saved to {Path(CLASSIFY_REPORT_FILE).resolve()}")
    except Exception as err:
        print(f"[WARNING] Could not save report to '{CLASSIFY_REPORT_FILE}': {err}")


def reconcile_only():
    """Standalone maintenance pass: drop the Newsletter label from any email that also
    carries newsletter-spam (fixes re-labels from 'Also apply filter to matching
    conversations'). No LLM calls, no publishing. Respects DRY_RUN."""
    print(f"\n[{datetime.now().isoformat()}] Starting quarantine reconciliation...")

    service = get_gmail_service()
    spam_label_id = get_or_create_label(service, NEWSLETTER_SPAM_LABEL)
    newsletter_label_id = get_or_create_label(service, NEWSLETTER_LABEL_NAME)

    fixed = reconcile_quarantine_labels(service, spam_label_id, newsletter_label_id)
    print(f"[INFO] Reconciliation complete: removed '{NEWSLETTER_LABEL_NAME}' from {fixed} email(s).")
    return fixed
