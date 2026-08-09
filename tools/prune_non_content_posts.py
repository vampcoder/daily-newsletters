#!/usr/bin/env python3
"""
prune_non_content_posts.py - Remove welcome emails, announcements, onboarding notes, and promotional offers from _posts/.
"""

import glob
import os
import re

PATTERNS = [
    r'\bwelcome to\b',
    r'\byou\'?re on the list\b',
    r'\bthanks for subscribing\b',
    r'\bgetting started with\b',
    r'\bunlock your ai engineering future\b',
    r'\bnow streaming on substack\b',
    r'\bcoming to you live\b',
    r'category:\s*"Announcement"',
    r'category:\s*"Marketing"',
    r'category:\s*"Promotional"'
]

def prune():
    files = glob.glob("_posts/*.md")
    removed_count = 0
    
    for filepath in files:
        filename = os.path.basename(filepath)
        try:
            content = open(filepath, encoding='utf-8').read()
            text_to_check = f"{filename}\n{content[:1000]}".lower()

            should_delete = False
            for pattern in PATTERNS:
                if re.search(pattern, text_to_check):
                    should_delete = True
                    break

            if should_delete:
                os.remove(filepath)
                print(f"[REMOVED] Pruned non-content / welcome post: {filename}")
                removed_count += 1

        except Exception as err:
            print(f"[ERROR] Could not inspect {filename}: {err}")

    print(f"\n[SUMMARY] Pruned {removed_count} welcome/announcement/promotional posts from _posts/.")

if __name__ == '__main__':
    prune()
