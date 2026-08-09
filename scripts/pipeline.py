import os
from datetime import datetime

# Import configurations
from scripts.config import (
    DRY_RUN,
    ENABLE_LLM_CURATION,
    LLM_API_KEY,
    MIN_RELEVANCE_SCORE
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
    mark_email_as_read
)

# Import GitHub helpers
from scripts.github_helper import get_github_repo, publish_to_github

# Import LLM curation calls
from scripts.llm_curator import curate_newsletter_with_llm

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
            kwargs = {'userId': 'me', 'q': 'label:newsletter', 'maxResults': 500}
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
