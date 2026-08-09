#!/usr/bin/env python3
"""
main.py - Automated Gmail Newsletter to GitHub Pages Pipeline with LLM Curation, Polishing & Dynamic Categorization.

Orchestration scheduler entrypoint. Imports execution pipelines from scripts/.
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
from scripts.pipeline import process_inbox


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
