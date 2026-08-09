import os
import re
import json
from typing import Optional
from pydantic import BaseModel, Field

try:
    import litellm
except ImportError:
    litellm = None

from scripts.config import ENABLE_LLM_CURATION, LLM_API_KEY, LLM_MODEL, LLM_API_BASE, MIN_RELEVANCE_SCORE


# Pydantic Schemas for Structured LLM Outputs
class CurationDecision(BaseModel):
    should_publish: bool = Field(description="True if email is a high quality newsletter worth reading, False if spam or marketing")
    relevance_score: int = Field(description="Relevance score from 1 (spam/promotional) to 10 (exceptional quality)")
    reason: str = Field(description="Brief rationale for curation decision")


class PolishedNewsletter(BaseModel):
    polished_title: str = Field(description="Catchy, professional, and clear post title")
    publisher: Optional[str] = Field(default=None, description="Exact publication or newsletter brand name")
    category: str = Field(description="Concise 1-3 word category. Pick from existing_categories if appropriate or invent a fitting new one")
    executive_summary: str = Field(description="2-3 sentence overview summary for preview tile card")
    key_takeaways: list[str] = Field(description="3-5 bullet point takeaways summarizing key insights")
    ad_blocks: list[str] = Field(default=[], description="Exact sentences, paragraphs or blocks in the email that represent sponsored ads, marketing pitches, or book/course promotion copy that should be deleted")


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

    prompt = f"""You are an editor curating a reading archive.
Evaluate this email and decide if it contains substantive reading content (informative articles, essays, technical deep-dives, market research, health/nutrition science notes, behavioral psychology, productivity lessons, or book summaries).

Sender: {sender}
Subject: {subject}
Content Preview: {body_preview[:800]}

STRICT REJECTION RULES (Mark should_publish = false & relevance_score < 5):
1. Plain subscription confirmations ("You're on the list", "Welcome to the newsletter", "Thanks for subscribing").
2. Pure marketing / sales / discount blasts ("50% off", "Cyber Monday", "Upgrade to paid membership", "Enroll in my masterclass" without any actual article text).
3. System notifications, billing alerts, or transactional emails.

PUBLICATION ALLOWANCE (Mark should_publish = true & relevance_score >= 8):
- If the email contains a nutrition/science essay (e.g. from Glucose Goddess), a self-improvement/mindset essay (e.g. from Mark Manson), a psychology/productivity breakdown (e.g. from Nir Eyal), a learning lesson (e.g. from Scott Young), or finance insights (e.g. from Dezerv/Value Research).
- Even if there are links to buy a book, enroll in a course, or social follow buttons at the very bottom, approve it if the core body is an educational article or essay.

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


def polish_newsletter_with_llm(subject, body_text, existing_categories, sender=None):
    """Stage 2: Polish title, extract key takeaways, assign dynamic category, and clean body."""
    if not ENABLE_LLM_CURATION or not LLM_API_KEY or not litellm:
        return None

    cats_str = ", ".join(existing_categories) if existing_categories else "None yet"
    body_snippet = body_text
    if len(body_text) > 7000:
        body_snippet = body_text[:4000] + "\n\n... [TRUNCATED MIDDLE CONTENT] ...\n\n" + body_text[-3000:]

    prompt = f"""You are an expert editor summarizing a newsletter post for a web archive.
Your job is to read the newsletter snippet and generate high-quality metadata (polished title, publisher, category, summary, bulleted key takeaways, and advertising blocks to remove).

Subject: {subject}
Sender Address: {sender}
Existing Categories in Repository: [{cats_str}]

Full Body Text Snippet:
{body_snippet}

Respond ONLY with a valid JSON object matching exact format:
{{
  "polished_title": "Clean catchy title",
  "publisher": "Exact publication or newsletter brand name (e.g. Interconnects, Readwise, The Ken, ByteByteGo, Substack)",
  "category": "Pick a meaningful content topic (e.g. Tech & AI, Finance & Investing, Healthcare & Medicine, Software Engineering, Productivity)",
  "executive_summary": "2-3 sentence overview summary for card preview",
  "key_takeaways": ["Takeaway 1", "Takeaway 2", "Takeaway 3"],
  "ad_blocks": ["Exact paragraph or sentences representing sponsored ads or pitches (e.g., 'This summary is brought to you by...') to delete"]
}}
"""

    try:
        kwargs = {
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "api_key": LLM_API_KEY,
            "response_format": {"type": "json_object"}
        }
        if LLM_API_BASE:
            kwargs["api_base"] = LLM_API_BASE

        response = litellm.completion(**kwargs)
        raw_content = response.choices[0].message.content
        data = extract_json_from_llm(raw_content)
        return PolishedNewsletter(**data)
    except Exception as err:
        print(f"[WARNING] LLM Curation Stage 2 error ({err}). Falling back to subject defaults.")
        return None
