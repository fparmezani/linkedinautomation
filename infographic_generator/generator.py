import json
import os
import re
import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _build_infographic_prompt(topic: str, lang: str) -> str:
    lang_name = "Português (Brasil)" if lang == "pt" else "English"

    return f"""You are a senior C# and .NET developer creating an INFOGRAPHIC for LinkedIn.
The infographic must be data-driven, visually structured, and highly shareable.

NICHE: Using Artificial Intelligence to write better C# code, be more productive,
and build smarter .NET applications.

Topic: {topic}
Language: {lang_name} — write EVERYTHING in this language

Return ONLY valid JSON — no markdown fences, no explanation.

JSON structure:
{{
  "topic": string,
  "title": string (max 60 chars, bold hook),
  "subtitle": string (max 100 chars, context line),
  "cover_tag": string (short label e.g. "IA + .NET"),
  "blocks": [
    {{
      "icon": string (single emoji),
      "stat": string (short number or keyword, e.g. "3x faster", "85%", "Top 5"),
      "label": string (max 30 chars, what the stat means),
      "detail": string (max 80 chars, one-line explanation)
    }}
  ],
  "tip": string (max 120 chars, one actionable developer tip),
  "footer_cta": string (max 60 chars, e.g. "Siga para mais dicas de IA + .NET"),
  "hashtags": [string, string, string, string, string]
}}

Rules:
- title: impactful, developer-focused, speaks to a pain point or insight
- blocks: exactly 5 blocks. Each with a compelling stat/number. Real data or realistic estimates.
  Mix of percentages, comparisons, rankings, time savings.
- tip: practical, actionable, something a dev can use TODAY
- footer_cta: short call to action
- hashtags: lowercase, no #, no spaces
- tone: data-driven, professional, developer-to-developer. No fluff."""


def _safe_parse_json(raw: str) -> dict:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse infographic JSON. Raw (first 300 chars): {raw[:300]}")


def generate_infographic(topic: str, lang: str) -> dict:
    prompt = _build_infographic_prompt(topic, lang)
    message = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    return _safe_parse_json(raw)
