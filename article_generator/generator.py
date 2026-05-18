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


def _build_article_prompt(topic: str, lang: str) -> str:
    lang_name = "Português (Brasil)" if lang == "pt" else "English"
    is_pt = lang == "pt"

    cta = (
        "Gostou do conteúdo? Me segue para mais artigos sobre IA e .NET toda semana!"
        if is_pt
        else "Found this useful? Follow me for weekly articles on AI and .NET!"
    )
    hashtags = (
        "dotnet csharp inteligenciaartificial ia produtividade desenvolvedor aspnetcore"
        if is_pt
        else "dotnet csharp artificialintelligence ai productivity developer aspnetcore"
    )

    return f"""You are a senior C# and .NET developer writing a **long-form LinkedIn article** that sounds
authentic, personal, and deeply technical. It should read like it was written by a real developer
who uses these tools daily — not by a content machine.

NICHE: Using Artificial Intelligence to write better C# code, be more productive,
and build smarter .NET applications.

Topic: {topic}
Language: {lang_name} — write EVERYTHING in this language

Return ONLY valid JSON — no markdown fences, no explanation, nothing else.

JSON structure (follow exactly):
{{
  "topic": string,
  "headline": string,
  "subheadline": string,
  "cover_tag": string,
  "reading_time_min": number,
  "post_text": string,
  "sections": [
    {{
      "heading": string,
      "body": string,
      "code_block": string | null,
      "code_language": string | null
    }}
  ],
  "conclusion": string,
  "cta": string,
  "hashtags": [string, string, string, string, string, string]
}}

Rules:
- headline: bold, hook-driven, max 80 chars — speaks directly to a developer pain point
- subheadline: 1-2 sentences expanding the headline, practical promise
- cover_tag: short label e.g. "IA + .NET", "Semantic Kernel", "GitHub Copilot", "ML.NET"
- reading_time_min: realistic estimate (typically 5-8 min for a 1200-1800 word article)
- post_text: the LinkedIn post that will accompany the article link. 3 short punchy paragraphs,
  developer voice. Ends with a hook to read the full article. NO hashtags here (they go separately).
- sections: 5 to 7 sections, each with:
    - heading: clear, descriptive, max 60 chars
    - body: 2-4 solid paragraphs with real developer insight. Write in first person occasionally
      ("I use this in production", "in my team we..."). Include concrete examples,
      gotchas, and recommendations. Min 120 words per section.
    - code_block: valid modern C# (.NET 8+) showing AI integration where applicable.
      Max 20 lines, realistic and production-quality. null if not applicable.
      CRITICAL: inside JSON strings, use \\n for newlines and \\" for quotes — the code_block
      value must be a single-line JSON string with all special chars properly escaped.
    - code_language: "csharp", "json", "bash" or null
- conclusion: 1-2 paragraphs wrapping up key takeaways. Personal tone.
- cta: "{cta}"
- hashtags: lowercase, no spaces, no #. Example tags: {hashtags}
- tone: developer-to-developer. Honest about trade-offs. Practical. Technically grounded.
  No buzzword soup. No corporate fluff. Reads like a dev blog post, not a marketing piece."""


def _safe_parse_json(raw: str) -> dict:
    """Try multiple strategies to extract valid JSON from the response."""
    # 1. Remove markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    # 2. Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 3. Find the outermost { ... } block
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    # 4. If still failing, re-ask Claude to fix the JSON
    raise ValueError(f"Could not parse JSON response. Raw (first 300 chars): {raw[:300]}")


def generate_article(topic: str, lang: str) -> dict:
    prompt = _build_article_prompt(topic, lang)

    # Use extended thinking budget to get clean, complete JSON
    message = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    return _safe_parse_json(raw)
