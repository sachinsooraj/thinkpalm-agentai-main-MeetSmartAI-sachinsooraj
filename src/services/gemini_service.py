"""
MeetSmart AI — Gemini LLM service.
Wraps google-generativeai with fallback to rule-based processing
if GEMINI_API_KEY is not set.
"""

import json
import re
import logging
from typing import Optional

from src.utils.config import settings

logger = logging.getLogger(__name__)

# Lazy-init Gemini client
_gemini_model = None


def _get_model():
    global _gemini_model
    if _gemini_model is None and settings.gemini_enabled:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            _gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            logger.info("✅ Gemini model initialised")
        except Exception as e:
            logger.warning(f"⚠️  Gemini init failed: {e}. Using rule-based fallback.")
    return _gemini_model


def _call_gemini(prompt: str) -> Optional[str]:
    model = _get_model()
    if model is None:
        return None
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None


# ── Notes processing ─────────────────────────────────────────────────────────

NOTES_PROMPT = """You are a professional meeting notes analyst. 
Analyse the following meeting transcript/notes and extract structured information.

TRANSCRIPT:
{transcript}

Return a JSON object (no markdown, raw JSON only) with this exact structure:
{{
  "summary": "2-3 sentence summary of the meeting",
  "decisions": ["decision 1", "decision 2", ...],
  "action_items": [
    {{
      "description": "clear action item description",
      "owner": "person's name or 'Team' if unclear",
      "deadline": "YYYY-MM-DD or 'TBD'",
      "priority": "high|medium|low"
    }}
  ],
  "key_topics": ["topic 1", "topic 2", ...]
}}
"""


def process_meeting_notes(transcript: str) -> dict:
    """
    Process meeting transcript and return structured notes.
    Uses Gemini if available, otherwise falls back to rule-based extraction.
    """
    if settings.gemini_enabled:
        prompt = NOTES_PROMPT.format(transcript=transcript)
        raw = _call_gemini(prompt)
        if raw:
            try:
                # Strip markdown code fences if present
                clean = re.sub(r"```(?:json)?", "", raw).strip()
                return json.loads(clean)
            except json.JSONDecodeError:
                logger.warning("Gemini returned invalid JSON — falling back to rule-based")

    return _rule_based_notes(transcript)


def _rule_based_notes(transcript: str) -> dict:
    """
    Rule-based extraction when Gemini is unavailable.
    Detects common patterns like 'action item:', 'decision:', 'TODO:', '@name'.
    """
    lines = transcript.strip().split("\n")

    action_items = []
    decisions = []
    key_topics = []

    action_patterns = re.compile(
        r"(action item|todo|follow.?up|assigned to|task|will do|needs to|should|must)[:\-\s]",
        re.IGNORECASE,
    )
    decision_patterns = re.compile(
        r"(decided|agreed|approved|confirmed|resolved|conclusion)[:\-\s]",
        re.IGNORECASE,
    )
    owner_pattern = re.compile(r"@(\w+)|(?:by|assigned to|owner)\s+([A-Z][a-z]+)", re.IGNORECASE)
    deadline_pattern = re.compile(
        r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|next week|EOD|EOM|Monday|Friday|tomorrow)\b",
        re.IGNORECASE,
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if action_patterns.search(line):
            owner_match = owner_pattern.search(line)
            owner = owner_match.group(1) or owner_match.group(2) if owner_match else "Team"
            deadline_match = deadline_pattern.search(line)
            deadline = deadline_match.group(0) if deadline_match else "TBD"
            action_items.append({
                "description": line[:200],
                "owner": owner,
                "deadline": deadline,
                "priority": "high" if "urgent" in line.lower() or "asap" in line.lower() else "medium",
            })
        elif decision_patterns.search(line):
            decisions.append(line[:200])

    # Simple summary: first 3 non-empty lines
    first_lines = [l.strip() for l in lines if l.strip()][:3]
    summary = " ".join(first_lines)[:500] if first_lines else "Meeting notes processed."

    # Key topics: extract nouns from first 10 lines (simple heuristic)
    topic_candidates = re.findall(r"\b([A-Z][a-zA-Z]{3,})\b", " ".join(first_lines[:10]))
    key_topics = list(dict.fromkeys(topic_candidates))[:8]  # unique, max 8

    return {
        "summary": summary,
        "decisions": decisions if decisions else ["No explicit decisions detected."],
        "action_items": action_items if action_items else [],
        "key_topics": key_topics,
        "mode": "rule-based",
    }
