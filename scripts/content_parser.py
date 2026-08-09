import os
import re
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup
import markdownify
from scripts.llm_curator import polish_newsletter_with_llm, ENABLE_LLM_CURATION, LLM_API_KEY

try:
    import litellm
except ImportError:
    litellm = None

from scripts.config import POSTS_DIR, THEME_GRADIENTS


def clean_html(raw_html):
    """Clean up raw HTML before parsing and markdown conversion."""
    soup = BeautifulSoup(raw_html, 'html.parser')
    for element in soup(['script', 'style', 'head', 'meta', 'link']):
        element.decompose()
    return soup


def extract_featured_image(soup):
    """Extract primary featured image URL while skipping tracking pixels and avatars."""
    images = soup.find_all('img')
    IGNORE_PATTERNS = ['pixel', 'avatar', 'icon', 'favicon', 'beacon', 'open.php', 'logo-small', '1x1', 'tracker', 'emoji', 'p.gif', '/o/', 'button', 'badge', 'subscribe', '/open', 'pstmrk.it', 'tracking', 'open?']

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
        if any(tracker in src_lower for tracker in IGNORE_PATTERNS):
            continue

        return src

    return None


def extract_best_image(html):
    """Extract primary featured image URL from raw HTML while skipping tracking pixels, social icons, and trackers."""
    if not html:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    images = soup.find_all('img')
    IGNORE_PATTERNS = [
        'pixel', 'avatar', 'icon', 'favicon', 'beacon', 'open.php', 'logo-small', 
        '1x1', 'tracker', 'emoji', 'p.gif', '/o/', 'button', 'badge', 'subscribe', 
        '/open', 'pstmrk.it', 'tracking', 'open?', 'facebook', 'twitter', 'linkedin', 
        'instagram', 'youtube', 'github', 'pinterest', 'feedburner', 'rss', 'logo'
    ]

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
        if any(tracker in src_lower for tracker in IGNORE_PATTERNS):
            continue

        return src

    return None


def split_the_batch_email(subject, html):
    """
    Split a DeepLearning.AI 'The Batch' email into Andrew's letter and individual news stories.
    Returns a list of dicts: [{'title': str, 'html': str}]
    """
    soup = BeautifulSoup(html, 'html.parser')
    headers = soup.find_all(['h2', 'h3'])
    
    SKIP_KEYWORDS = [
        'dear friends', 'subscribe', 'deeplearning.ai', 'the batch', 
        'jobs', 'events', 'community', 'share', 'read online', 
        'view in browser', 'forwarded this email', 'about the author'
    ]
    
    valid_headers = []
    for h in headers:
        text = h.get_text().strip()
        text_lower = text.lower()
        if not text or len(text) < 5 or len(text) > 120:
            continue
        if any(kw in text_lower for kw in SKIP_KEYWORDS):
            continue
        valid_headers.append(h)
        
    posts = []
    letter_title = subject
    if 'the batch:' in letter_title.lower():
        letter_title = re.sub(r'(?i)^the batch:\s*', '', letter_title)
    letter_title = f"Andrew's Letter: {letter_title}"
    
    if not valid_headers:
        return [{'title': letter_title, 'html': html}]
        
    serialized_html = str(soup)
    indices = []
    for h in valid_headers:
        h_str = str(h)
        idx = serialized_html.find(h_str)
        if idx != -1:
            indices.append((idx, h_str, h.get_text().strip()))
            
    indices.sort(key=lambda x: x[0])
    
    # 1. Andrew's Letter
    first_idx = indices[0][0]
    posts.append({
        'title': letter_title,
        'html': serialized_html[:first_idx]
    })
    
    # 2. News stories
    for i in range(len(indices)):
        start_idx = indices[i][0]
        title = indices[i][2]
        if i + 1 < len(indices):
            end_idx = indices[i+1][0]
            section_html = serialized_html[start_idx:end_idx]
        else:
            section_html = serialized_html[start_idx:]
            
        posts.append({
            'title': title,
            'html': section_html
        })
        
    return posts


def get_gradient_theme(subject):
    """Generate a deterministic background gradient based on subject string."""
    hash_num = int(hashlib.md5(subject.encode('utf-8')).hexdigest(), 16)
    return THEME_GRADIENTS[hash_num % len(THEME_GRADIENTS)]


def detect_summary_and_cta(soup, subject):
    """Detect if newsletter is a teaser summary pointing to a main link and extract video/pdf links."""
    links = soup.find_all('a', href=True)
    summary_keywords = ['read full', 'read online', 'view in browser', 'continue reading', 'read more', 'read post', 'open in app', 'read on substack']

    primary_link = None
    is_summary = False
    video_url = None
    pdf_url = None

    for a in links:
        text = a.get_text().strip().lower()
        href = a['href']
        if not href.startswith('http'):
            continue

        if any(kw in text for kw in summary_keywords):
            primary_link = href
            is_summary = True

        if 'video' in text or 'youtube.com' in href or 'youtu.be' in href:
            if not video_url:
                video_url = href
        if 'pdf' in text or 'download' in text or 'filekitcdn' in href:
            if not pdf_url:
                pdf_url = href

    text_content = soup.get_text().strip()
    if len(text_content) < 400 and links:
        is_summary = True
        if not primary_link:
            primary_link = links[0]['href']

    return is_summary, primary_link, video_url, pdf_url


def extract_excerpt(soup):
    """Extract a 2-sentence excerpt preview for the tile card."""
    text = soup.get_text(separator=' ').strip()
    text = re.sub(r'\s+', ' ', text)
    if len(text) > 180:
        return text[:177] + "..."
    return text or "Click to read full newsletter."


def slugify(text):
    """Convert subject line to safe URL and filename slug."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-') or 'newsletter'


def get_existing_categories(posts_directory=None):
    """Scan existing Markdown posts in _posts/ and collect all assigned categories."""
    if posts_directory is None:
        posts_directory = POSTS_DIR
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


def build_jekyll_markdown(subject, sender, email_dt, raw_html, existing_categories=None):
    """Clean HTML, extract metadata, run LLM enrichment if enabled, and return Jekyll doc."""
    soup = clean_html(raw_html)

    featured_image = extract_best_image(raw_html)
    gradient_theme = get_gradient_theme(subject)
    is_summary, original_url, video_url, pdf_url = detect_summary_and_cta(soup, subject)
    default_excerpt = extract_excerpt(soup)
    source_name = sender.split('<')[0].strip(' "\'') if '<' in sender else (sender or "Newsletter")

    # Convert cleaned HTML body to Markdown
    raw_markdown_content = markdownify.markdownify(
        str(soup),
        heading_style="ATX",
        strip=['script', 'style', 'table', 'tr', 'td', 'tbody', 'thead']
    ).strip()

    # Stage 2 LLM Polishing & Dynamic Categorization
    polished_title = subject
    assigned_category = "General"
    executive_summary = default_excerpt
    key_takeaways = []

    def clean_unwanted_patterns(markdown_text):
        # Remove zero-width spaces and zero-width non-joiners
        markdown_text = markdown_text.replace('\u200b', '').replace('\u200c', '')

        # Remove unsubscribe links
        markdown_text = re.sub(r'\[Unsubscribe\]\([^)]+\)', '', markdown_text, flags=re.IGNORECASE)
        markdown_text = re.sub(r'\[Update your profile\]\([^)]+\)', '', markdown_text, flags=re.IGNORECASE)
        markdown_text = re.sub(r'\[View in (?:browser|web)\]\([^)]+\)', '', markdown_text, flags=re.IGNORECASE)
        # Remove ConvertKit/Substack signature addresses
        markdown_text = re.sub(r'\d+ [\w\s\.,#\-]+ (?:St|Ave|Ste|PMB|Rd|Blvd|Street|Avenue)[^\n]+, [A-Za-z\s]+ \d{5}(?:-\d{4})?', '', markdown_text, flags=re.IGNORECASE)
        
        # Clean empty markdown table grids that markdownify generates from outer spacer tables
        markdown_text = re.compile(r'^\|[\s\|-]*\|$', re.MULTILINE).sub('', markdown_text)
        markdown_text = re.compile(r'^\|[\s:-]*\|$', re.MULTILINE).sub('', markdown_text)
        
        # Format spacing: replace double-space cell separators with paragraph breaks
        markdown_text = re.sub(r'([,\.!\?\w]) {2,}([A-Z0-9\[])', r'\1\n\n\2', markdown_text)
        
        # Ensure list items start on a fresh newline
        markdown_text = re.sub(r' {2,}(\d+\.\s)', r'\n\n\1', markdown_text)
        markdown_text = re.sub(r'([^\n])(\d+\.\s)', r'\1\n\n\2', markdown_text)

        # Clean empty links e.g. [](https://...)
        markdown_text = re.sub(r'\[\s*\]\([^)]+\)', '', markdown_text)

        # Remove trailing single parenthesis or brackets left from broken link cleans
        markdown_text = re.sub(r'\s*[\.!\?\)]+\s*$', '.', markdown_text)
        # Strip trailing table artifacts and spaces
        markdown_text = re.sub(r'\s*[\|\s\-]+$', '', markdown_text)
        # Clean extra divider lines
        markdown_text = re.sub(r'-{3,}', '---', markdown_text)
        
        # Line-by-line cleaning: strip leading and trailing whitespace, and indent
        # list item paragraph descriptions by 4 spaces to preserve continuous list numbering.
        cleaned_lines = []
        in_list = False
        for line in markdown_text.split('\n'):
            stripped = line.strip()
            
            # If line is a numbered list item
            if re.match(r'^\d+\.\s+', stripped):
                in_list = True
                cleaned_lines.append(stripped)
            # If line starts with divider, heading, bullet list or signature, reset list context
            elif stripped.startswith('---') or stripped.startswith('#') or stripped.startswith('*') or stripped.startswith('-') or stripped.startswith('Best,') or stripped.startswith('Share '):
                in_list = False
                cleaned_lines.append(stripped)
            elif in_list:
                if stripped == '':
                    cleaned_lines.append('')
                else:
                    # Indent child text block by 4 spaces
                    cleaned_lines.append('    ' + stripped)
            else:
                cleaned_lines.append(stripped)
                
        markdown_text = '\n'.join(cleaned_lines)
        
        # Remove redundant multiple consecutive newlines (3 or more -> 2 newlines)
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
        
        return markdown_text.strip()

    final_body_markdown = clean_unwanted_patterns(raw_markdown_content)

    if ENABLE_LLM_CURATION and LLM_API_KEY and litellm:
        polished_result = polish_newsletter_with_llm(
            subject, final_body_markdown, existing_categories or [], sender=sender
        )
        if polished_result:
            polished_title = polished_result.polished_title or subject
            if polished_result.publisher:
                source_name = polished_result.publisher
            assigned_category = polished_result.category or "General"
            executive_summary = polished_result.executive_summary or default_excerpt
            key_takeaways = polished_result.key_takeaways or []
            
            # Remove any ad blocks identified by the LLM from the body text
            if polished_result.ad_blocks:
                print(f"[DEBUG] Found {len(polished_result.ad_blocks)} ad blocks from LLM.")
                
                def remove_ad_block_fuzzily(body_text, ad_block):
                    ad_block_clean = ad_block.strip().replace("\\'", "'").replace('\\"', '"')
                    
                    # Try direct literal match first
                    if ad_block_clean.lower() in body_text.lower():
                        pattern = re.compile(re.escape(ad_block_clean), re.IGNORECASE)
                        return pattern.sub('', body_text)
                        
                    # Fuzzy match lookup
                    def simplify(s):
                        # Strip markdown links e.g. [Link](url) -> Link
                        s_no_links = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
                        return "".join(c for c in s_no_links.lower() if c.isalnum())

                    simplified_ad = simplify(ad_block_clean)
                    if not simplified_ad or len(simplified_ad) < 10:
                        return body_text

                    simplified_body = []
                    char_map = []
                    
                    i = 0
                    in_link_url = False
                    in_link_bracket = False
                    
                    while i < len(body_text):
                        char = body_text[i]
                        
                        if char == '[':
                            in_link_bracket = True
                        elif char == ']':
                            in_link_bracket = False
                        elif char == '(' and not in_link_bracket and i > 0 and body_text[i-1] == ']':
                            in_link_url = True
                            i += 1
                            continue
                        elif char == ')' and in_link_url:
                            in_link_url = False
                            i += 1
                            continue
                            
                        if in_link_url:
                            i += 1
                            continue
                            
                        if char.isalnum():
                            simplified_body.append(char.lower())
                            char_map.append(i)
                        i += 1
                        
                    simplified_body_str = "".join(simplified_body)
                    
                    start_sim_idx = simplified_body_str.find(simplified_ad)
                    if start_sim_idx != -1:
                        end_sim_idx = start_sim_idx + len(simplified_ad) - 1
                        start_orig_idx = char_map[start_sim_idx]
                        end_orig_idx = char_map[end_sim_idx] + 1
                        
                        # Consume trailing markdown link url if we cut off inside a markdown link anchor
                        rest_of_text = body_text[end_orig_idx:]
                        match = re.match(r'^(?:\s*\]\([^)]+\))?(?:\*\*|__|\"|\'|\*|\s)*', rest_of_text)
                        if match:
                            end_orig_idx += match.end()
                            
                        print(f"[FUZZY] Successfully matched and removed ad block: '{ad_block_clean[:60]}...' ")
                        return body_text[:start_orig_idx] + body_text[end_orig_idx:]
                        
                    print(f"[DEBUG] Failed to match ad block: '{ad_block_clean[:60]}...' ")
                    return body_text

                normalized_body = final_body_markdown.replace('\r\n', '\n')
                for block in polished_result.ad_blocks:
                    normalized_body = remove_ad_block_fuzzily(normalized_body, block)
                
                final_body_markdown = normalized_body
                
                # Clean up remaining hanging markdown elements (like divider blocks around the ad)
                final_body_markdown = re.sub(r'---\s*\n\s*\n\s*---', '---', final_body_markdown)

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

    if video_url:
        front_matter_lines.append(f'video_url: "{video_url}"')

    if pdf_url:
        front_matter_lines.append(f'pdf_url: "{pdf_url}"')

    front_matter_lines.append(f'is_summary: {"true" if is_summary else "false"}')

    if key_takeaways:
        front_matter_lines.append("key_takeaways:")
        for t in key_takeaways:
            escaped_t = t.replace('"', '\\"')
            front_matter_lines.append(f'  - "{escaped_t}"')

    front_matter_lines.append("---\n\n")

    return "\n".join(front_matter_lines) + final_body_markdown, is_summary, executive_summary, featured_image
