"""
Pesquisa topicos em alta no nicho C# .NET + Inteligencia Artificial.

Fontes:
  - dev.to      (tags: dotnet, csharp, ai, semantickernel, copilot)
  - Reddit      (r/dotnet, r/csharp, r/MachineLearning filtrado por .NET)
  - Hacker News (queries: semantic kernel, copilot csharp, dotnet AI, ML.NET)
  - Microsoft DevBlog (.NET + AI posts recentes)
  - Google Trends (queries em alta — requer pytrends, falha silenciosa)
"""

import os
import json
import re
import requests
import anthropic
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env", override=True)

_HTTP_TIMEOUT = 10
_HEADERS = {"User-Agent": "dotnet-bot/1.0 (linkedin automation, educational)"}

NICHE_FOCUS = "C# .NET development enhanced by Artificial Intelligence and AI tools"


# ── Fontes ────────────────────────────────────────────────────────────────────

def _fetch_devto() -> list:
    """Busca artigos no dev.to com tags de .NET e AI."""
    items = []
    tags = ["dotnet", "csharp", "ai", "semantickernel", "machinelearning", "copilot", "aspnet"]
    for tag in tags:
        try:
            r = requests.get(
                f"https://dev.to/api/articles?tag={tag}&top=7&per_page=6",
                headers=_HEADERS, timeout=_HTTP_TIMEOUT
            )
            if r.ok:
                for a in r.json()[:4]:
                    title = a.get("title", "")
                    items.append({
                        "title":     title,
                        "tags":      a.get("tag_list", []),
                        "reactions": a.get("public_reactions_count", 0),
                        "source":    "dev.to",
                    })
        except Exception:
            pass
    # deduplicate
    seen, unique = set(), []
    for it in items:
        if it["title"] not in seen:
            seen.add(it["title"])
            unique.append(it)
    return sorted(unique, key=lambda x: x["reactions"], reverse=True)[:12]


def _fetch_reddit() -> list:
    """Busca posts no Reddit focando em .NET + AI."""
    items = []
    subs = ["dotnet", "csharp", "aspnetcore", "MachineLearning", "LocalLLaMA"]
    for sub in subs:
        try:
            r = requests.get(
                f"https://www.reddit.com/r/{sub}/top.json?t=week&limit=10",
                headers=_HEADERS, timeout=_HTTP_TIMEOUT
            )
            if r.ok:
                for post in r.json()["data"]["children"][:5]:
                    d = post["data"]
                    title = d.get("title", "")
                    items.append({
                        "title":    title,
                        "score":    d.get("score", 0),
                        "comments": d.get("num_comments", 0),
                        "source":   f"r/{sub}",
                    })
        except Exception:
            pass
    return sorted(items, key=lambda x: x["score"], reverse=True)[:14]


def _fetch_hackernews() -> list:
    """Busca stories no HN sobre .NET e AI."""
    items = []
    queries = [
        "semantic kernel", "copilot csharp", "dotnet AI",
        "ML.NET", "C# LLM", "dotnet openai", "azure openai dotnet",
        "csharp machine learning"
    ]
    for q in queries:
        try:
            r = requests.get(
                f"https://hn.algolia.com/api/v1/search?query={q}&tags=story&hitsPerPage=5",
                headers=_HEADERS, timeout=_HTTP_TIMEOUT
            )
            if r.ok:
                for hit in r.json().get("hits", [])[:3]:
                    items.append({
                        "title":  hit.get("title", ""),
                        "points": hit.get("points", 0),
                        "source": "Hacker News",
                    })
        except Exception:
            pass
    seen, unique = set(), []
    for it in items:
        if it["title"] not in seen:
            seen.add(it["title"])
            unique.append(it)
    return sorted(unique, key=lambda x: x["points"], reverse=True)[:10]


def _fetch_ms_devblog() -> list:
    """Busca posts recentes do blog oficial .NET da Microsoft via RSS."""
    items = []
    feeds = [
        "https://devblogs.microsoft.com/dotnet/feed/",
        "https://devblogs.microsoft.com/visualstudio/feed/",
    ]
    for feed_url in feeds:
        try:
            r = requests.get(feed_url, headers=_HEADERS, timeout=_HTTP_TIMEOUT)
            if r.ok:
                # Parse simples de RSS — extrai titulos entre <title> tags
                titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", r.text)
                if not titles:
                    titles = re.findall(r"<title>(.*?)</title>", r.text)
                for title in titles[1:9]:  # pula o titulo do canal
                    clean = re.sub(r"<[^>]+>", "", title).strip()
                    if clean:
                        items.append({
                            "title":  clean,
                            "points": 0,
                            "source": "MS DevBlog",
                        })
        except Exception:
            pass
    return items[:10]


def _fetch_google_trends() -> list:
    """Busca queries em alta via pytrends (falha silenciosa se nao instalado)."""
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="en-US", tz=300, timeout=(10, 30))
        pt.build_payload(
            ["semantic kernel", "github copilot", "ML.NET"],
            timeframe="now 7-d"
        )
        related = pt.related_queries()
        items = []
        for term, data in related.items():
            if data and data.get("rising") is not None:
                for _, row in data["rising"].head(4).iterrows():
                    items.append({
                        "title":  row["query"],
                        "value":  int(row["value"]),
                        "source": "Google Trends",
                    })
        return items[:8]
    except Exception:
        return []


# ── Claude analysis ───────────────────────────────────────────────────────────

def _build_prompt(sources: dict, used_topics: list) -> str:
    def fmt_list(items, key="title", extra=None):
        lines = []
        for it in items[:12]:
            line = f"  - {it[key]}"
            if extra and it.get(extra):
                line += f"  [{it[extra]} pts]"
            lines.append(line)
        return "\n".join(lines) if lines else "  (sem dados)"

    used_str = "\n".join(f"  - {t}" for t in used_topics[-15:]) if used_topics else "  (nenhum)"

    return f"""You are a content strategist for a LinkedIn account focused on a very specific niche:

NICHE: "{NICHE_FOCUS}"

The audience is mid-to-senior C# / .NET developers who want to use AI tools and techniques
to write better code, be more productive, and build smarter applications.

Analyze the trending signals below and return the 10 BEST carousel post topics for this niche.

─── DEV.TO (top articles this week) ───
{fmt_list(sources.get('devto', []))}

─── REDDIT (r/dotnet, r/csharp, r/MachineLearning — top this week) ───
{fmt_list(sources.get('reddit', []))}

─── HACKER NEWS ───
{fmt_list(sources.get('hn', []), extra='points')}

─── MICROSOFT DEVBLOG (recent posts) ───
{fmt_list(sources.get('msdevblog', []))}

─── GOOGLE TRENDS (rising queries) ───
{fmt_list(sources.get('trends', []))}

─── Already posted recently (DO NOT repeat) ───
{used_str}

RULES:
1. Every topic MUST fit the niche: C# .NET + AI. Examples of good angles:
   - Using GitHub Copilot / Cursor to speed up C# development
   - Building AI features in ASP.NET Core (OpenAI, Claude, Gemini APIs)
   - Semantic Kernel: agents, plugins, memory in C#
   - ML.NET for classification/prediction in .NET apps
   - Prompt engineering tips specifically for C# developers
   - AI-assisted refactoring, code review, test generation in C#
   - Azure AI services integrated with .NET
   - Building RAG (Retrieval-Augmented Generation) systems in C#
2. Topics must be practical and actionable — real C# code examples possible
3. Trending signal from the sources above should inform choices
4. Do NOT repeat topics already posted
5. Each topic must work as a 6-slide carousel

Return ONLY valid JSON, no markdown:
{{
  "topics": [
    {{
      "rank": 1,
      "topic": "specific actionable topic (max 60 chars)",
      "angle": "hook for the carousel — what the reader will learn (max 80 chars)",
      "reasoning": "1-2 sentences: why this topic now, what trending signal supports it",
      "sources": ["dev.to", "reddit"]
    }},
    ...10 items total
  ]
}}
"""


def _ask_claude(prompt: str) -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ── Public API ────────────────────────────────────────────────────────────────

def research_trending_topic(used_topics: list = None) -> dict:
    """
    Pesquisa tendencias no nicho C# .NET + AI e retorna 10 opcoes de topico.

    Retorna:
    {
        "topics": [
            {"rank", "topic", "angle", "reasoning", "sources"},
            ...10 items
        ],
        "raw_sources": dict  # titulos brutos de cada fonte (debug)
    }
    """
    print("  Buscando dev.to...",        end=" ", flush=True)
    devto     = _fetch_devto();       print(f"{len(devto)} artigos")

    print("  Buscando Reddit...",        end=" ", flush=True)
    reddit    = _fetch_reddit();      print(f"{len(reddit)} posts")

    print("  Buscando Hacker News...",   end=" ", flush=True)
    hn        = _fetch_hackernews();  print(f"{len(hn)} stories")

    print("  Buscando MS DevBlog...",    end=" ", flush=True)
    msdevblog = _fetch_ms_devblog();  print(f"{len(msdevblog)} posts")

    print("  Buscando Google Trends...", end=" ", flush=True)
    trends    = _fetch_google_trends()
    print(f"{len(trends)} queries" if trends else "indisponivel")

    sources = {
        "devto":     devto,
        "reddit":    reddit,
        "hn":        hn,
        "msdevblog": msdevblog,
        "trends":    trends,
    }

    print("  Analisando com Claude...", end=" ", flush=True)
    prompt = _build_prompt(sources, used_topics or [])
    result = _ask_claude(prompt)
    print("ok")

    result["raw_sources"] = {
        "devto":     [i["title"] for i in devto[:5]],
        "reddit":    [i["title"] for i in reddit[:5]],
        "hn":        [i["title"] for i in hn[:5]],
        "msdevblog": [i["title"] for i in msdevblog[:5]],
        "trends":    [i["title"] for i in trends[:5]],
    }

    # Normalise: garante que sempre existe "topics"
    if "topics" not in result and "topic" in result:
        result["topics"] = [{
            "rank":      1,
            "topic":     result["topic"],
            "angle":     result.get("angle", ""),
            "reasoning": result.get("reasoning", ""),
            "sources":   result.get("sources_used", []),
        }]
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from content_generator.generator import load_topics

    data = load_topics()
    used = [t["topic"] for t in data.get("used", [])]

    print("\n[dotnet-bot] Pesquisando topicos em alta — nicho: C# .NET + AI\n")
    result = research_trending_topic(used_topics=used)

    print("\n" + "=" * 60)
    print("  10 TOPICOS C# .NET + AI\n")
    for t in result.get("topics", []):
        print(f"  #{t['rank']:2d}  {t['topic']}")
        print(f"       Angulo  : {t['angle']}")
        print(f"       Fontes  : {', '.join(t.get('sources', []))}")
        print(f"       Por que : {t['reasoning'][:100]}...")
        print()
    print("=" * 60 + "\n")
