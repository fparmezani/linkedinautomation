import json
import os
import re
import anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

TOPICS_FILE = os.path.join(os.path.dirname(__file__), "topics_queue.json")
_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def load_topics() -> dict:
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_topics(data: dict):
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_next_topic() -> dict:
    data = load_topics()
    if not data["available"]:
        data["available"] = data["used"]
        data["used"] = []
        save_topics(data)
    return data["available"][0]


def mark_topic_used(topic_id: int):
    data = load_topics()
    topic = next((t for t in data["available"] if t["id"] == topic_id), None)
    if topic:
        data["available"].remove(topic)
        data["used"].append(topic)
        save_topics(data)


def _build_prompt(topic: str, lang: str) -> str:
    lang_name = "Portuguese (Brazil)" if lang == "pt" else "English"
    cta_hint = (
        "Curtiu? Salva e compartilha com a galera!" if lang == "pt"
        else "Found this useful? Save it and share!"
    )
    hashtag_hint = (
        "dotnet, csharp, ia, inteligenciaartificial, desenvolvedor"
        if lang == "pt"
        else "dotnet, csharp, ai, artificialintelligence, devproductivity"
    )
    return f"""You are creating a LinkedIn carousel post for mid-to-senior C# and .NET developers.

NICHE: Using Artificial Intelligence to write better C# code, be more productive,
and build smarter .NET applications.

Topic: {topic}
Language: {lang_name} — write EVERYTHING in this language (titles, points, post_text, all text)

Generate exactly 6 slides. Return ONLY valid JSON — no markdown fences, no explanation, nothing else.

JSON structure (follow exactly):
{{
  "topic": string,
  "post_text": string,
  "slides": [
    {{"type": "cover",   "title": string, "subtitle": string, "tag": string}},
    {{"type": "content", "title": string, "points": [string, string, string], "code": null}},
    {{"type": "content", "title": string, "points": [string, string], "code": string}},
    {{"type": "code",    "title": string, "description": string, "code": string}},
    {{"type": "content", "title": string, "points": [string, string, string], "code": null}},
    {{"type": "cta",     "title": string, "text": string, "hashtags": [string, string, string, string, string]}}
  ]
}}

Rules:
- post_text: 2-3 short paragraphs in developer voice, showing how AI improves .NET development;
  end with 5 hashtags on a new line
- cover title: max 35 chars — punchy, AI-angle hook
- cover tag: short category label e.g. "AI + .NET", "Semantic Kernel", "GitHub Copilot"
- slide titles: max 40 chars
- bullet points: max 68 chars each, start with a verb or key fact; focus on practical AI usage
- code: valid modern C# (.NET 8+), shows AI integration (API calls, Semantic Kernel, ML.NET, etc.)
  when applicable; realistic and copy-paste useful; max 10 lines
- cta title hint: "{cta_hint}"
- hashtags: lowercase, no spaces — mix of .NET and AI tags, e.g. {hashtag_hint}
- tone: developer-to-developer, direct, enthusiastic about AI but technically grounded,
  no corporate fluff, no buzzword soup"""


def generate_carousel(topic: str, lang: str) -> dict:
    prompt = _build_prompt(topic, lang)
    message = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)
