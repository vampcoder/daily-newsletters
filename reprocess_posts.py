#!/usr/bin/env python3
"""
reprocess_posts.py - Batch enhance top N existing Markdown posts in _posts/ using DeepSeek LLM.
Generates clean, valid YAML front-matter with titles, real publisher brand names, categories, summaries, and key takeaways.
"""

import glob
import hashlib
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

# Material UI Color Palettes (gradients from materialui.co)
THEME_GRADIENTS = [
    "linear-gradient(135deg, #673ab7 0%, #512da8 100%)",  # Deep Purple
    "linear-gradient(135deg, #3f51b5 0%, #303f9f 100%)",  # Indigo
    "linear-gradient(135deg, #009688 0%, #00796b 100%)",  # Teal
    "linear-gradient(135deg, #e91e63 0%, #c2185b 100%)",  # Pink
    "linear-gradient(135deg, #00bcd4 0%, #0097a7 100%)",  # Cyan
    "linear-gradient(135deg, #ff5722 0%, #e64a19 100%)",  # Deep Orange
    "linear-gradient(135deg, #9c27b0 0%, #7b1fa2 100%)",  # Purple
    "linear-gradient(135deg, #2196f3 0%, #1976d2 100%)",  # Blue
    "linear-gradient(135deg, #4caf50 0%, #388e3c 100%)",  # Green
    "linear-gradient(135deg, #ff9800 0%, #f57c00 100%)",  # Amber
    "linear-gradient(135deg, #607d8b 0%, #455a64 100%)",  # Blue Grey
    "linear-gradient(135deg, #f44336 0%, #d32f2f 100%)"   # Red
]

def get_gradient_theme(text):
    hash_num = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)
    return THEME_GRADIENTS[hash_num % len(THEME_GRADIENTS)]

def get_existing_categories():
    categories = set()
    for filepath in glob.glob("_posts/*.md"):
        try:
            content = open(filepath, encoding='utf-8').read()
            match = re.search(r'^category:\s*"([^"]+)"', content, re.MULTILINE)
            if match and match.group(1) not in ('General', 'Announcement'):
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
            
            parts = raw.split('---\n', 2)
            if len(parts) < 3:
                parts = raw.split('---', 2)
            
            fm_text = parts[1] if len(parts) >= 3 else ""
            body_text = parts[2] if len(parts) >= 3 else raw

            date_match = re.search(r'^date:\s*(.+)$', fm_text, re.MULTILINE)
            image_match = re.search(r'^image:\s*"([^"]+)"', fm_text, re.MULTILINE) or re.search(r'^image:\s*(.+)$', fm_text, re.MULTILINE)
            original_url_match = re.search(r'^original_url:\s*"([^"]+)"', fm_text, re.MULTILINE) or re.search(r'^original_url:\s*(.+)$', fm_text, re.MULTILINE)
            is_summary = 'is_summary: true' in fm_text

            post_date = date_match.group(1).strip() if date_match else ""
            post_image = image_match.group(1).strip().strip('"\'') if image_match else ""
            post_url = original_url_match.group(1).strip().strip('"\'') if original_url_match else ""

            title_match = re.search(r'^title:\s*"([^"]+)"', fm_text, re.MULTILINE) or re.search(r'^title:\s*(.+)$', fm_text, re.MULTILINE)
            subject = title_match.group(1).strip().strip('"\'') if title_match else "Newsletter"

            existing_cats = get_existing_categories()
            cats_str = ", ".join(existing_cats) if existing_cats else "None yet"
            print(f"[{i+1}/{len(files)}] Extracting Publisher & Polishing: {os.path.basename(filepath)}...")

            prompt = f"""You are an expert technical editor polishing a newsletter post for a web archive.

Subject: {subject}
Existing Categories in Repository: [{cats_str}]

Full Body Text:
{body_text[:3500]}

Respond ONLY with a valid JSON object matching exact format:
{{
  "polished_title": "Clean catchy title",
  "publisher": "Exact publication or newsletter brand name (e.g. Interconnects, Readwise, The Ken, ByteByteGo, Substack, Wisereads, Astral Codex Ten)",
  "category": "Pick a meaningful content topic (e.g. Tech & AI, Finance & Investing, Healthcare & Medicine, Software Engineering, Productivity)",
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
            publisher = res.get('publisher', 'Newsletter')
            category = res.get('category', 'Tech & AI')
            executive_summary = res.get('executive_summary', '')
            key_takeaways = res.get('key_takeaways', [])
            cleaned_markdown = res.get('cleaned_markdown', body_text)
            gradient = get_gradient_theme(polished_title)

            # Rebuild clean YAML front-matter
            fm_lines = [
                "---",
                "layout: post",
                f'title: "{polished_title.replace('"', '\\"')}"',
                f'date: {post_date}',
                f'source: "{publisher.replace('"', '\\"')}"',
                f'category: "{category.replace('"', '\\"')}"',
                f'excerpt: "{executive_summary.replace('"', '\\"')}"',
                f'theme_gradient: "{gradient}"',
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

            print(f"[SUCCESS] Enhanced post: {os.path.basename(filepath)} | Title: {polished_title} | Publisher: {publisher} | Category: {category}")

        except Exception as err:
            print(f"[ERROR] Failed reprocessing {os.path.basename(filepath)}: {err}")

if __name__ == '__main__':
    reprocess_top_n(limit=5)
