#!/usr/bin/env python3
"""
main.py - Automated Gmail Newsletter to GitHub Pages Pipeline with LLM Curation, Polishing & Dynamic Categorization.

Fetches unread newsletter emails from Gmail, uses a 2-Stage LLM Pipeline (LiteLLM + DeepSeek/OpenAI compatible)
to filter spam, generate catchy titles, extract 💡 key takeaways, assign dynamic categories,
converts content to Jekyll Markdown with rich front-matter, publishes to GitHub, and marks emails as read.
"""

import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from github import Github, Auth, GithubException, UnknownObjectException
import markdownify
import schedule
from pydantic import BaseModel, Field

try:
    import litellm
except ImportError:
    litellm = None

# Load local .env file if available
load_dotenv()

# Configuration from environment variables
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
TOKEN_FILE = Path(os.getenv('TOKEN_FILE', 'token.json'))
CREDENTIALS_FILE = Path(os.getenv('CREDENTIALS_FILE', 'credentials.json'))
FETCH_INTERVAL_HOURS = int(os.getenv('FETCH_INTERVAL_HOURS', '4'))
POSTS_DIR = os.getenv('POSTS_DIR', '_posts').strip('/')
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() in ('true', '1', 'yes')

# LLM Configuration (DeepSeek / OpenAI compatible via LiteLLM)
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek/deepseek-chat')
LLM_API_BASE = os.getenv('LLM_API_BASE', 'https://api.deepseek.com')
ENABLE_LLM_CURATION = os.getenv('ENABLE_LLM_CURATION', 'true').lower() in ('true', '1', 'yes')
MIN_RELEVANCE_SCORE = int(os.getenv('MIN_RELEVANCE_SCORE', '6'))

# Curated gradient palettes for fallback tile image headers
THEME_GRADIENTS = [
    "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
    "linear-gradient(135deg, #0284c7 0%, #0d9488 100%)",
    "linear-gradient(135deg, #d97706 0%, #dc2626 100%)",
    "linear-gradient(135deg, #2563eb 0%, #3b82f6 100%)",
    "linear-gradient(135deg, #059669 0%, #10b981 100%)",
    "linear-gradient(135deg, #9333ea 0%, #c026d3 100%)",
    "linear-gradient(135deg, #e11d48 0%, #f43f5e 100%)",
    "linear-gradient(135deg, #0891b2 0%, #06b6d4 100%)"
]

# Rule-based Spam / Promo filtering patterns (Pre-filter before LLM)
PROMO_KEYWORDS = [
    r'\b% off\b', r'\bdiscount\b', r'\bsale\b', r'\bcoupon\b', r'\bpromo code\b',
    r'\blimited time offer\b', r'\bbuy now\b', r'\bblack friday\b', r'\bcyber monday\b',
    r'\bsponsored\b', r'\bfree trial\b', r'\bcheckout\b', r'\border summary\b', r'\binvoice\b'
]


# Pydantic Schemas for Structured LLM Outputs
class CurationDecision(BaseModel):
    should_publish: bool = Field(description="True if email is a high quality newsletter worth reading, False if spam or marketing")
    relevance_score: int = Field(description="Relevance score from 1 (spam/promotional) to 10 (exceptional quality)")
    reason: str = Field(description="Brief rationale for curation decision")


class PolishedNewsletter(BaseModel):
    polished_title: str = Field(description="Catchy, professional, and clear post title")
    category: str = Field(description="Concise 1-3 word category. Pick from existing_categories if appropriate or invent a fitting new one")
    executive_summary: str = Field(description="2-3 sentence overview summary for preview tile card")
    key_takeaways: list[str] = Field(description="3-5 bullet point takeaways summarizing key insights")
    cleaned_markdown: str = Field(description="Cleaned post body in Markdown, removing footers, sponsor ads, unsubscribe links")


def get_github_token():
    """Retrieve GitHub token from environment variable or gh CLI."""
    token = os.getenv('GITHUB_TOKEN')
    if token and token != "ghp_your_personal_access_token_here":
        return token

    try:
        gh_token = subprocess.check_output(['gh', 'auth', 'token'], text=True).strip()
        if gh_token:
            return gh_token
    except Exception:
        pass

    return None


GITHUB_REPO = os.getenv('GITHUB_REPO', 'vampcoder/daily-newsletters')


def get_gmail_service():
    """Load session token, refresh if expired, and return Gmail API service."""
    if not TOKEN_FILE.exists():
        raise FileNotFoundError(
            f"Token file '{TOKEN_FILE}' not found. Please run 'python auth_setup.py' first."
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        print("[INFO] Gmail OAuth token expired. Refreshing token...")
        creds.refresh(Request())
        with open(TOKEN_FILE, 'w', encoding='utf-8') as token_out:
            token_out.write(creds.to_json())

    if not creds or not creds.valid:
        raise ValueError("Invalid credentials. Please re-run auth_setup.py.")

    return build('gmail', 'v1', credentials=creds)


def get_github_repo():
    """Initialize Github API client and return target repository."""
    token = get_github_token()
    if not token:
        raise ValueError("GitHub Token not found. Log in with `gh auth login` or set GITHUB_TOKEN.")

    auth = Auth.Token(token)
    gh_client = Github(auth=auth)
    return gh_client.get_repo(GITHUB_REPO)


def extract_header_value(headers, name):
    """Retrieve header value by case-insensitive name match."""
    for header in headers:
        if header.get('name', '').lower() == name.lower():
            return header.get('value', '')
    return ''


def slugify(text):
    """Convert subject line to safe URL and filename slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-') or 'newsletter'


def parse_email_parts(payload):
    """Recursively extract raw HTML or plain text body from email payload."""
    html_body = None
    text_body = None

    def _walk_parts(part):
        nonlocal html_body, text_body
        mime_type = part.get('mimeType', '')
        body = part.get('body', {})
        data = body.get('data')

        if data:
            decoded_bytes = base64.urlsafe_b64decode(data.encode('UTF-8'))
            decoded_content = decoded_bytes.decode('utf-8', errors='replace')
            if mime_type == 'text/html' and not html_body:
                html_body = decoded_content
            elif mime_type == 'text/plain' and not text_body:
                text_body = decoded_content

        parts = part.get('parts', [])
        for sub_part in parts:
            _walk_parts(sub_part)

    _walk_parts(payload)
    return html_body or text_body or "<p>No content extracted from email.</p>"


def is_promotional_email(subject, sender, text_body):
    """Check if email is marketing spam, welcome email, discount blast, or announcement."""
    content_sample = f"{subject} {sender} {text_body[:500]}".lower()
    for pattern in PROMO_KEYWORDS:
        if re.search(pattern, content_sample):
            return True
    return False


def clean_html(raw_html):
    """Clean up raw HTML before parsing and markdown conversion."""
    soup = BeautifulSoup(raw_html, 'html.parser')
    for element in soup(['script', 'style', 'head', 'meta', 'link']):
        element.decompose()
    return soup


def extract_featured_image(soup):
    """Extract primary featured image URL while skipping tracking pixels and avatars."""
    images = soup.find_all('img')
    for img in images:
        src = img.get('src') or img.get('data-src')
        if not src or not src.startswith('http'):
            continue

        width = img.get('width')
        height = img.get('height')
        if width and (width == '1' or width == '0'):
            continue
        if height and (height == '1' or height == '0'):
            continue

        src_lower = src.lower()
        if any(tracker in src_lower for tracker in [
            'p.gif', 'pixel.gif', 'beacon.gif', 'open.php', 'track.gif',
            'avatar', 'icon', 'favicon', 'logo-small', '1x1'
        ]):
            continue

        return src

    return None


def get_gradient_theme(subject):
    """Generate a deterministic background gradient based on subject string."""
    hash_num = int(hashlib.md5(subject.encode('utf-8')).hexdigest(), 16)
    return THEME_GRADIENTS[hash_num % len(THEME_GRADIENTS)]


def detect_summary_and_cta(soup, subject):
    """Detect if newsletter is a teaser summary pointing to a main link."""
    links = soup.find_all('a', href=True)
    summary_keywords = ['read full', 'read online', 'view in browser', 'continue reading', 'read more', 'read post', 'open in app', 'read on substack']

    primary_link = None
    is_summary = False

    for a in links:
        text = a.get_text().strip().lower()
        href = a['href']
        if not href.startswith('http'):
            continue

        if any(kw in text for kw in summary_keywords):
            primary_link = href
            is_summary = True
            break

    text_content = soup.get_text().strip()
    if len(text_content) < 400 and links:
        is_summary = True
        if not primary_link:
            primary_link = links[0]['href']

    return is_summary, primary_link


def extract_excerpt(soup):
    """Extract a 2-sentence excerpt preview for the tile card."""
    text = soup.get_text(separator=' ').strip()
    text = re.sub(r'\s+', ' ', text)
    if len(text) > 180:
        return text[:177] + "..."
    return text or "Click to read full newsletter."


def parse_email_date(date_str):
    """Parse RFC 2822 date header into datetime object."""
    if date_str:
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            pass
    return datetime.now(timezone.utc)


def extract_newsletter_source(sender):
    """Clean sender name (e.g. 'ByteByteGo <newsletter@domain.com>' -> 'ByteByteGo')."""
    if '<' in sender:
        name = sender.split('<')[0].strip(' "\'')
        if name:
            return name
    return sender or "Newsletter"


def get_existing_categories(posts_directory=POSTS_DIR):
    """Scan existing Markdown posts in _posts/ and collect all assigned categories."""
    categories = set()
    posts_path = Path(posts_directory)
    if not posts_path.exists():
        return list(categories)

    for file_path in posts_path.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
            match = re.search(r'^category:\s*"([^"]+)"', content, re.MULTILINE) or re.search(r'^category:\s*(.+)$', content, re.MULTILINE)
            if match:
                cat = match.group(1).strip().strip('"\'')
                if cat and cat not in ('General', 'Announcement'):
                    categories.add(cat)
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

    # Clean trailing commas in JSON arrays/objects
    text = re.sub(r',\s*([\]}])', r'\1', text)

    return json.loads(text)



def curate_newsletter_with_llm(subject, sender, body_preview):
    """Stage 1: Lightweight LLM Curation Gate (~150 tokens)."""
    if not ENABLE_LLM_CURATION or not LLM_API_KEY or not litellm:
        return True, 7, "LLM curation disabled or API key missing."

    prompt = f"""You are a strict technical editor curating a high-signal professional reading archive.
Evaluate the following email to decide whether it contains real, substantive reading content (articles, technical essays, deep-dives, market insights, news analysis).

Sender: {sender}
Subject: {subject}
Content Preview: {body_preview[:800]}

STRICT REJECTION RULES (Mark should_publish = false & relevance_score < 5):
1. Welcome / Onboarding / Subscription Confirmation emails ("Welcome to...", "You're on the list", "Thanks for subscribing").
2. Promotional / Marketing / Sales / Discount offers ("50% off", "Limited offer inside", "Upgrade to paid", "Course enrollment").
3. Announcements / System / Substack notifications ("Now streaming on Substack", "Coming to you live", "Platform update").
4. Transactional emails (receipts, password resets, billing alerts, invoices).

PUBLICATION CRITERIA (Mark should_publish = true & relevance_score >= 6 ONLY if):
- The email contains a real informative article, engineering analysis, finance breakdown, industry insight, or essay worth reading.

Respond ONLY with a valid JSON object matching exact format:
{{
  "should_publish": true,
  "relevance_score": 8,
  "reason": "Brief rationale"
}}
"""

    try:
        kwargs = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "api_key": LLM_API_KEY
        }
        if LLM_API_BASE:
            kwargs["api_base"] = LLM_API_BASE

        response = litellm.completion(**kwargs)
        raw_content = response.choices[0].message.content
        data = extract_json_from_llm(raw_content)
        return data.get("should_publish", True), data.get("relevance_score", 7), data.get("reason", "")
    except Exception as err:
        print(f"[WARNING] LLM Curation Stage 1 error ({err}). Falling back to rule decision.")
        return True, 7, f"Fallback due to error: {err}"


def polish_newsletter_with_llm(subject, body_text, existing_categories):
    """Stage 2: Polish title, extract key takeaways, assign dynamic category, and clean body."""
    if not ENABLE_LLM_CURATION or not LLM_API_KEY or not litellm:
        return None

    cats_str = ", ".join(existing_categories) if existing_categories else "None yet"

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

    try:
        kwargs = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "api_key": LLM_API_KEY
        }
        if LLM_API_BASE:
            kwargs["api_base"] = LLM_API_BASE

        response = litellm.completion(**kwargs)
        raw_content = response.choices[0].message.content
        data = extract_json_from_llm(raw_content)
        return PolishedNewsletter(
            polished_title=data.get("polished_title", subject),
            category=data.get("category", "General"),
            executive_summary=data.get("executive_summary", ""),
            key_takeaways=data.get("key_takeaways", []),
            cleaned_markdown=data.get("cleaned_markdown", body_text)
        )
    except Exception as err:
        print(f"[WARNING] LLM Polishing Stage 2 error ({err}).")
        return None



def build_jekyll_markdown(subject, sender, email_dt, raw_html, existing_categories=None):
    """Clean HTML, extract metadata, run LLM enrichment if enabled, and return Jekyll doc."""
    soup = clean_html(raw_html)

    featured_image = extract_featured_image(soup)
    gradient_theme = get_gradient_theme(subject)
    is_summary, original_url = detect_summary_and_cta(soup, subject)
    default_excerpt = extract_excerpt(soup)
    source_name = extract_newsletter_source(sender)

    # Convert cleaned HTML body to Markdown
    raw_markdown_content = markdownify.markdownify(
        str(soup),
        heading_style="ATX",
        strip=['script', 'style']
    ).strip()

    # Stage 2 LLM Polishing & Dynamic Categorization
    polished_title = subject
    assigned_category = "General"
    executive_summary = default_excerpt
    key_takeaways = []
    final_body_markdown = raw_markdown_content

    if ENABLE_LLM_CURATION and LLM_API_KEY and litellm:
        polished_result = polish_newsletter_with_llm(
            subject, raw_markdown_content, existing_categories or []
        )
        if polished_result:
            polished_title = polished_result.polished_title or subject
            assigned_category = polished_result.category or "General"
            executive_summary = polished_result.executive_summary or default_excerpt
            key_takeaways = polished_result.key_takeaways or []
            if polished_result.cleaned_markdown and len(polished_result.cleaned_markdown) > 50:
                final_body_markdown = polished_result.cleaned_markdown

    formatted_date = email_dt.strftime('%Y-%m-%d %H:%M:%S %z')
    escaped_title = polished_title.replace('"', '\\"')
    escaped_excerpt = executive_summary.replace('"', '\\"')
    escaped_source = source_name.replace('"', '\\"')
    escaped_category = assigned_category.replace('"', '\\"')

    front_matter_lines = [
        "---",
        "layout: post",
        f'title: "{escaped_title}"',
        f"date: {formatted_date}",
        f'source: "{escaped_source}"',
        f'category: "{escaped_category}"',
        f'excerpt: "{escaped_excerpt}"',
        f'theme_gradient: "{gradient_theme}"',
    ]

    if featured_image:
        front_matter_lines.append(f'image: "{featured_image}"')

    if original_url:
        front_matter_lines.append(f'original_url: "{original_url}"')

    front_matter_lines.append(f'is_summary: {"true" if is_summary else "false"}')

    if key_takeaways:
        front_matter_lines.append("key_takeaways:")
        for t in key_takeaways:
            escaped_t = t.replace('"', '\\"')
            front_matter_lines.append(f'  - "{escaped_t}"')

    front_matter_lines.append("---\n\n")

    return "\n".join(front_matter_lines) + final_body_markdown, is_summary, executive_summary, featured_image


def publish_to_github(repo, filename, content, subject):
    """Publish or update Markdown post in target GitHub repository."""
    path = f"{POSTS_DIR}/{filename}" if POSTS_DIR else filename
    commit_message = f"Add newsletter: {subject}"

    if DRY_RUN or repo is None:
        local_path = Path(path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(content, encoding='utf-8')
        print(f"[DRY-RUN] Saved post locally to: {local_path.resolve()}")
        return

    try:
        existing_file = repo.get_contents(path)
        print(f"[INFO] Updating existing post on GitHub: {path}")
        repo.update_file(
            path=path,
            message=f"Update newsletter: {subject}",
            content=content,
            sha=existing_file.sha
        )
        print(f"[SUCCESS] Updated post on GitHub: {path}")
    except (UnknownObjectException, GithubException) as ge:
        if getattr(ge, 'status', None) in (404,):
            print(f"[INFO] Creating new post on GitHub: {path}")
            try:
                repo.create_file(path=path, message=commit_message, content=content)
                print(f"[SUCCESS] Created post on GitHub: {path}")
                return
            except Exception as create_err:
                print(f"[WARNING] Create file failed ({create_err}), attempting update fallback...")

        # SHA mismatch or conflict fallback: fetch latest sha and update
        try:
            latest = repo.get_contents(path)
            repo.update_file(path=path, message=f"Update newsletter: {subject}", content=content, sha=latest.sha)
            print(f"[SUCCESS] Updated post on GitHub (with fresh SHA): {path}")
        except Exception as err:
            print(f"[ERROR] Could not publish post '{path}' to GitHub: {err}")



def mark_email_as_read(service, msg_id):
    """Remove UNREAD label from processed email."""
    if DRY_RUN:
        print(f"[DRY-RUN] Would mark email ID '{msg_id}' as READ.")
        return

    service.users().messages().modify(
        userId='me',
        id=msg_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()
    print(f"[SUCCESS] Marked email ID '{msg_id}' as READ.")


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

        results = service.users().messages().list(
            userId='me',
            q='label:newsletter is:unread'
        ).execute()

        messages = results.get('messages', [])
        if not messages:
            print("[INFO] No unread newsletter emails found matching 'label:newsletter is:unread'.")
            return

        print(f"[INFO] Found {len(messages)} unread newsletter email(s).")

        for msg_summary in messages:
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

                # Rule-based Pre-Filter
                if is_promotional_email(subject, sender, raw_html):
                    print(f"[SKIP] Pre-filter promotional email skipped: '{subject}' ({msg_id})")
                    mark_email_as_read(service, msg_id)
                    continue

                # Stage 1: LLM Curation Gate
                if ENABLE_LLM_CURATION and LLM_API_KEY and litellm:
                    should_pub, score, reason = curate_newsletter_with_llm(subject, sender, raw_html)
                    print(f"[LLM-GATE] Score: {score}/10 | Publish: {should_pub} | Rationale: {reason}")
                    if not should_pub or score < MIN_RELEVANCE_SCORE:
                        print(f"[SKIP] LLM Curation filtered out low relevance email: '{subject}'")
                        mark_email_as_read(service, msg_id)
                        continue

                print(f"[INFO] Processing newsletter: '{subject}' ({msg_id})")

                markdown_doc, is_summary, excerpt, img_url = build_jekyll_markdown(
                    subject, sender, email_dt, raw_html, existing_categories
                )

                date_prefix = email_dt.strftime('%Y-%m-%d')
                subject_slug = slugify(subject)
                filename = f"{date_prefix}-{subject_slug}.md"

                publish_to_github(repo, filename, markdown_doc, subject)
                if repo is not None:
                    mark_email_as_read(service, msg_id)

            except Exception as item_err:
                print(f"[ERROR] Failed to process email ID '{msg_id}': {item_err}")

    except Exception as batch_err:
                print(f"[ERROR] Batch execution error: {batch_err}")


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
