#!/usr/bin/env python3
"""
main.py - Automated Gmail Newsletter to GitHub Pages Pipeline with LLM Curation, Polishing & Dynamic Categorization.

Orchestration scheduler entrypoint. Imports execution pipelines from scripts/.

Modes:
  python main.py            Run the scheduler (publish pipeline every FETCH_INTERVAL_HOURS)
  python main.py --once     Run the publish pipeline once, then exit
  python main.py --classify LLM decides newsletter vs spam for every email under
                            label:newsletter and prints a plain YES/NO report. Nothing is
                            published or modified. (Also: CLASSIFY_ONLY=true env var)
  python main.py --classify --apply-labels
                            Same as --classify, but NO-verdict emails are labeled
                            'newsletter-spam' and unlabeled from 'Newsletter' (also:
                            CLASSIFY_APPLY_LABELS=true env var). Respects DRY_RUN.
  python main.py --reconcile Maintenance: remove 'Newsletter' from any email that also
                            has 'newsletter-spam' (safety net after re-running a Gmail
                            filter with 'Also apply...'). No LLM calls.
"""

import os
import sys
import time
import schedule

# Import configuration constants
from scripts.config import (
    FETCH_INTERVAL_HOURS,
    POSTS_DIR,
    DRY_RUN,
    GITHUB_REPO,
    ENABLE_LLM_CURATION,
    LLM_MODEL,
    MIN_RELEVANCE_SCORE
)

# Import the core pipeline processor
from scripts.pipeline import process_inbox, classify_inbox, reconcile_only


def main():
    print("=" * 60)
    print("      Gmail Newsletter to GitHub Pages Pipeline Service      ")
    print("=" * 60)
    print(f"[CONFIG] Target Repo: {GITHUB_REPO}")
    print(f"[CONFIG] Post Directory: {POSTS_DIR}")
    print(f"[CONFIG] Schedule Interval: Every {FETCH_INTERVAL_HOURS} hour(s)")
    print(f"[CONFIG] LLM Curation Enabled: {ENABLE_LLM_CURATION}")
    if ENABLE_LLM_CURATION:
        print(f"[CONFIG] LLM Model: {LLM_MODEL}")
        print(f"[CONFIG] Min Relevance Score: {MIN_RELEVANCE_SCORE}")
    if DRY_RUN:
        print("[CONFIG] Mode: DRY_RUN (saving files locally)")

    if '--reconcile' in sys.argv:
        print("[CONFIG] Mode: RECONCILE_ONLY (quarantine integrity pass — no LLM, no publishing)")
        reconcile_only()
        print("\n[INFO] Reconciliation run completed. Exiting.")
        return

    classify_only = '--classify' in sys.argv or os.getenv('CLASSIFY_ONLY', 'false').lower() in ('true', '1', 'yes')
    if classify_only:
        apply_labels = ('--apply-labels' in sys.argv
                        or os.getenv('CLASSIFY_APPLY_LABELS', 'false').lower() in ('true', '1', 'yes'))
        print("[CONFIG] Mode: CLASSIFY_ONLY (LLM spam report — nothing is published)")
        if apply_labels:
            print("[CONFIG] Applying labels to NO verdicts: add 'newsletter-spam', remove 'Newsletter'")
        classify_inbox(apply_labels=apply_labels)
        print("\n[INFO] Classification run completed. Exiting.")
        return

    run_once = '--once' in sys.argv or os.getenv('RUN_ONCE', 'false').lower() in ('true', '1', 'yes')

    process_inbox()

    if run_once:
        print("\n[INFO] Single run mode completed (--once). Exiting.")
        return

    schedule.every(FETCH_INTERVAL_HOURS).hours.do(process_inbox)

    print(f"\n[INFO] Scheduler active. Running every {FETCH_INTERVAL_HOURS} hour(s). Press Ctrl+C to stop.")
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n[INFO] Service stopped by user.")
            sys.exit(0)
        except Exception as loop_err:
            print(f"[WARNING] Event loop exception encountered: {loop_err}")
            time.sleep(60)


if __name__ == '__main__':
    main()
