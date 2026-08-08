#!/usr/bin/env python3
"""
reprocess_posts.py - Batch enhance top N existing Markdown posts in _posts/ using DeepSeek LLM.
Generates clean, valid YAML front-matter with titles, dynamic categories, summaries, and key takeaways.
"""

import glob
import json
import os
import re
from pathlib import Path
import litellm
from dotenv import load_dotenv

load_dotenv()

LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek/deepseek-chat')
LLM_API_BASE = os.getenv('LLM_API_BASE', 'https://api.deepseek.com')

def get_existing_categories():
    categories = set()
    for filepath in glob.glob("_posts/*.md"):
        try:
            content = open(filepath, encoding='utf-8').read()
            match = re.search(r'^category:\s*"([^"]+)"', content, re.MULTILINE)
            if match and match.group(1) != 'General':
                categories.add(match.group(1))
        except Exception:
            pass
    return sorted(list(categories))

def extract_json_from_llm(text):
    """Extract and parse JSON object from LLM response text."""
    text = text.strip()
    if text.startswith("```json"):
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif text.startswith("```"):
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        text = match.group(0)
    
    text = re.sub(r',\s*([\]}])', r'\1', text)
    return json.loads(text)

def reprocess_top_n(limit=5):
    files = sorted(glob.glob("_posts/*.md"), reverse=True)[:limit]
    print(f"[INFO] Polishing top {len(files)} newest post files with DeepSeek LLM...")

    for i, filepath in enumerate(files):
        try:
            raw = open(filepath, encoding='utf-8').read()
            
            # Parse existing front-matter fields
            parts = raw.split('---\n', 2)
            if len(parts) < 3:
                # If first delimiter missing
                parts = raw.split('---', 2)
            
            fm_text = parts[1] if len(parts) >= 3 else ""
            body_text = parts[2] if len(parts) >= 3 else raw

            date_match = re.search(r'^date:\s*(.+)$', fm_text, re.MULTILINE)
            source_match = re.search(r'^source:\s*"([^"]+)"', fm_text, re.MULTILINE) or re.search(r'^source:\s*(.+)$', fm_text, re.MULTILINE)
            image_match = re.search(r'^image:\s*"([^"]+)"', fm_text, re.MULTILINE) or re.search(r'^image:\s*(.+)$', fm_text, re.MULTILINE)
            original_url_match = re.search(r'^original_url:\s*"([^"]+)"', fm_text, re.MULTILINE) or re.search(r'^original_url:\s*(.+)$', fm_text, re.MULTILINE)
            is_summary = 'is_summary: true' in fm_text

            post_date = date_match.group(1).strip() if date_match else ""
            post_source = source_match.group(1).strip().strip('"\'') if source_match else "Newsletter"
            post_image = image_match.group(1).strip().strip('"\'') if image_match else ""
            post_url = original_url_match.group(1).strip().strip('"\'') if original_url_match else ""

            title_match = re.search(r'^title:\s*"([^"]+)"', fm_text, re.MULTILINE) or re.search(r'^title:\s*(.+)$', fm_text, re.MULTILINE)
            subject = title_match.group(1).strip().strip('"\'') if title_match else "Newsletter"

            existing_cats = get_existing_categories()
            cats_str = ", ".join(existing_cats) if existing_cats else "None yet"
            print(f"[{i+1}/{len(files)}] Polishing with DeepSeek LLM: {os.path.basename(filepath)}...")

            prompt = f"""You are an expert technical editor polishing a newsletter post for a web archive.

Subject: {subject}
Existing Categories in Repository: [{cats_str}]

Full Body Text:
{body_text[:3500]}

Respond ONLY with a valid JSON object matching exact format:
{{
  "polished_title": "Clean catchy title",
  "category": "Pick a meaningful content topic (e.g. Tech & AI, Finance & Investing, Healthcare & Medicine, Software Engineering, Productivity). DO NOT use 'Announcement', 'General', or 'Marketing'",
  "executive_summary": "2-3 sentence overview summary for card preview",
  "key_takeaways": ["Takeaway 1", "Takeaway 2", "Takeaway 3"],
  "cleaned_markdown": "Cleaned post body text removing unsubscribe footers, email headers, and ads"
}}
"""


            kwargs = {
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "api_key": LLM_API_KEY,
            }
            if LLM_API_BASE:
                kwargs["api_base"] = LLM_API_BASE

            response = litellm.completion(**kwargs)
            raw_ans = response.choices[0].message.content
            res = extract_json_from_llm(raw_ans)

            polished_title = res.get('polished_title', subject)
            category = res.get('category', 'General')
            executive_summary = res.get('executive_summary', '')
            key_takeaways = res.get('key_takeaways', [])
            cleaned_markdown = res.get('cleaned_markdown', body_text)

            # Rebuild clean YAML front-matter
            fm_lines = [
                "---",
                "layout: post",
                f'title: "{polished_title.replace('"', '\\"')}"',
                f'date: {post_date}',
                f'source: "{post_source.replace('"', '\\"')}"',
                f'category: "{category.replace('"', '\\"')}"',
                f'excerpt: "{executive_summary.replace('"', '\\"')}"',
            ]
            if post_image:
                fm_lines.append(f'image: "{post_image}"')
            if post_url:
                fm_lines.append(f'original_url: "{post_url}"')
            fm_lines.append(f'is_summary: {"true" if is_summary else "false"}')
            if key_takeaways:
                fm_lines.append("key_takeaways:")
                for t in key_takeaways:
                    fm_lines.append(f'  - "{t.replace('"', '\\"')}"')
            fm_lines.append("---\n\n")

            cleaned_body = cleaned_markdown if (cleaned_markdown and len(cleaned_markdown) > 50) else body_text
            new_doc = "\n".join(fm_lines) + cleaned_body

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_doc)

            print(f"[SUCCESS] Enhanced post: {os.path.basename(filepath)} | Title: {polished_title} | Category: {category}")

        except Exception as err:
            print(f"[ERROR] Failed reprocessing {os.path.basename(filepath)}: {err}")

if __name__ == '__main__':
    reprocess_top_n(limit=5)
