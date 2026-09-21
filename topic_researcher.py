"""
Pesquisa topicos em alta no nicho C# .NET + Inteligencia Artificial.

Fontes:
  - dev.to      (tags: dotnet, csharp, ai, semantickernel, copilot)
  - Reddit      (r/dotnet, r/csharp, r/MachineLearning filtrado por .NET)
  - Hacker News (queries: semantic kernel, copilot csharp, dotnet AI, ML.NET)
  - Microsoft DevBlog (.NET + AI posts recentes)
  - GitHub Trending (repos C# em alta)
  - Stack Overflow (perguntas populares C# + AI)
  - Hashnode     (artigos .NET + AI)
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


def _fetch_github_trending() -> list:
    """Busca repos C# em trending no GitHub."""
    items = []
    try:
        r = requests.get(
            "https://api.github.com/search/repositories?q=language:csharp+topic:ai+topic:machine-learning&sort=stars&order=desc&per_page=10",
            headers={**_HEADERS, "Accept": "application/vnd.github.v3+json"},
            timeout=_HTTP_TIMEOUT
        )
        if r.ok:
            for repo in r.json().get("items", [])[:10]:
                items.append({
                    "title":  f"{repo['name']}: {repo.get('description', '')[:80]}",
                    "points": repo.get("stargazers_count", 0),
                    "source": "GitHub Trending",
                })
    except Exception:
        pass
    # Also search for recent AI + dotnet repos
    try:
        r = requests.get(
            "https://api.github.com/search/repositories?q=dotnet+AI+pushed:>2024-01-01&sort=updated&order=desc&per_page=10",
            headers={**_HEADERS, "Accept": "application/vnd.github.v3+json"},
            timeout=_HTTP_TIMEOUT
        )
        if r.ok:
            for repo in r.json().get("items", [])[:8]:
                items.append({
                    "title":  f"{repo['name']}: {repo.get('description', '')[:80]}",
                    "points": repo.get("stargazers_count", 0),
                    "source": "GitHub Trending",
                })
    except Exception:
        pass
    seen, unique = set(), []
    for it in items:
        if it["title"] not in seen:
            seen.add(it["title"])
            unique.append(it)
    return sorted(unique, key=lambda x: x["points"], reverse=True)[:12]


def _fetch_stackoverflow() -> list:
    """Busca perguntas populares recentes no SO sobre C# + AI."""
    items = []
    tags_combos = ["c%23;artificial-intelligence", "c%23;openai", ".net;machine-learning",
                   "c%23;azure-cognitive-services", "semantic-kernel"]
    for tags in tags_combos:
        try:
            r = requests.get(
                f"https://api.stackexchange.com/2.3/questions?order=desc&sort=activity&tagged={tags}&site=stackoverflow&pagesize=5&filter=default",
                headers=_HEADERS, timeout=_HTTP_TIMEOUT
            )
            if r.ok:
                for q in r.json().get("items", [])[:4]:
                    items.append({
                        "title":  q.get("title", ""),
                        "points": q.get("score", 0),
                        "source": "Stack Overflow",
                    })
        except Exception:
            pass
    seen, unique = set(), []
    for it in items:
        if it["title"] not in seen:
            seen.add(it["title"])
            unique.append(it)
    return sorted(unique, key=lambda x: x["points"], reverse=True)[:10]


def _fetch_hashnode() -> list:
    """Busca artigos em alta no Hashnode sobre .NET + AI."""
    items = []
    try:
        query = {
            "query": """query {
                searchPostsOfFeed(first: 10, filter: { query: "dotnet AI csharp" }) {
                    edges {
                        node {
                            title
                            reactionCount
                        }
                    }
                }
            }"""
        }
        r = requests.post(
            "https://gql.hashnode.com",
            json=query,
            headers={**_HEADERS, "Content-Type": "application/json"},
            timeout=_HTTP_TIMEOUT
        )
        if r.ok:
            edges = r.json().get("data", {}).get("searchPostsOfFeed", {}).get("edges", [])
            for edge in edges[:8]:
                node = edge.get("node", {})
                items.append({
                    "title":  node.get("title", ""),
                    "points": node.get("reactionCount", 0),
                    "source": "Hashnode",
                })
    except Exception:
        pass
    return items[:8]


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

    used_str = "\n".join(f"  - {t}" for t in used_topics) if used_topics else "  (nenhum)"

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

─── GITHUB TRENDING (C# + AI repos) ───
{fmt_list(sources.get('github', []), extra='points')}

─── STACK OVERFLOW (popular C# + AI questions) ───
{fmt_list(sources.get('stackoverflow', []), extra='points')}

─── HASHNODE (articles) ───
{fmt_list(sources.get('hashnode', []), extra='points')}

─── GOOGLE TRENDS (rising queries) ───
{fmt_list(sources.get('trends', []))}

─── Already posted / queued (DO NOT suggest ANY of these) ───
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
4. CRITICAL: Do NOT repeat or rephrase ANY topic from the "Already posted / queued" list above.
   If a topic is similar to one already listed, skip it entirely. Choose a DIFFERENT angle.
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

def _is_too_similar(new_topic: str, existing: list, threshold: float = 0.55) -> bool:
    """Check if new_topic is too similar to any existing topic using word overlap."""
    new_words = set(new_topic.lower().split())
    # Remove very common words
    stop = {"a", "an", "the", "in", "on", "for", "to", "with", "and", "or", "of",
            "your", "how", "using", "use", "com", "para", "como", "seu", "sua", "no", "na", "de", "do"}
    new_words -= stop
    if not new_words:
        return False
    for existing_topic in existing:
        ex_words = set(existing_topic.lower().split()) - stop
        if not ex_words:
            continue
        overlap = len(new_words & ex_words) / min(len(new_words), len(ex_words))
        if overlap >= threshold:
            return True
    return False


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

    print("  Buscando GitHub Trending...", end=" ", flush=True)
    github    = _fetch_github_trending(); print(f"{len(github)} repos")

    print("  Buscando Stack Overflow...", end=" ", flush=True)
    stackoverflow = _fetch_stackoverflow(); print(f"{len(stackoverflow)} perguntas")

    print("  Buscando Hashnode...",       end=" ", flush=True)
    hashnode  = _fetch_hashnode();        print(f"{len(hashnode)} artigos")

    print("  Buscando Google Trends...", end=" ", flush=True)
    trends    = _fetch_google_trends()
    print(f"{len(trends)} queries" if trends else "indisponivel")

    sources = {
        "devto":         devto,
        "reddit":        reddit,
        "hn":            hn,
        "msdevblog":     msdevblog,
        "github":        github,
        "stackoverflow": stackoverflow,
        "hashnode":      hashnode,
        "trends":        trends,
    }

    print("  Analisando com Claude...", end=" ", flush=True)
    prompt = _build_prompt(sources, used_topics or [])
    result = _ask_claude(prompt)
    print("ok")

    result["raw_sources"] = {
        "devto":         [i["title"] for i in devto[:5]],
        "reddit":        [i["title"] for i in reddit[:5]],
        "hn":            [i["title"] for i in hn[:5]],
        "msdevblog":     [i["title"] for i in msdevblog[:5]],
        "github":        [i["title"] for i in github[:5]],
        "stackoverflow": [i["title"] for i in stackoverflow[:5]],
        "hashnode":      [i["title"] for i in hashnode[:5]],
        "trends":        [i["title"] for i in trends[:5]],
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

    # Post-filter: remove tópicos similares a já usados/fila (Claude nem sempre respeita)
    if used_topics:
        filtered = [t for t in result.get("topics", [])
                    if not _is_too_similar(t["topic"], used_topics)]
        if filtered:
            result["topics"] = filtered
            # Re-rank
            for i, t in enumerate(result["topics"], 1):
                t["rank"] = i

    return result


def generate_titles_from_idea(idea: str, content_type: str = "post") -> dict:
    """
    Generates 5 alternative titles/topics from a user's idea customized by content type.

    Returns:
    {
        "titles": [
            {"rank": 1, "title": "...", "description": "..."},
            ...5 items
        ]
    }
    """
    # Customize guidelines based on content type
    if content_type == "article":
        type_desc = "deep-dive technical articles (suitable for LinkedIn articles or Substack posts)"
        specific_rules = """1. Are practical and detailed, suitable for an in-depth article or tutorial with code snippets
2. Focus on conceptual clarity, best practices, or step-by-step implementations
3. Fit within the niche of C# / .NET enhanced by AI"""
    elif content_type == "infographic":
        type_desc = "visual infographics (suitable for cheat sheets, diagrams, comparisons, or step-by-step visual flows)"
        specific_rules = """1. Are visual-friendly, structured around steps, checklists, architecture, or comparisons (e.g. 'A vs B', '5 steps to...', 'Cheat Sheet')
2. Can be summarized in a single, high-impact diagram or visual table
3. Fit within the niche of C# / .NET enhanced by AI"""
    else:  # post
        type_desc = "carousel posts (suitable for a 6-slide LinkedIn carousel)"
        specific_rules = """1. Are highly practical and actionable, designed to be digested in a slide-by-slide format
2. Can be explained well in a 6-slide visual deck
3. Fit within the niche of C# / .NET enhanced by AI"""

    prompt = f"""You are a content strategist for a LinkedIn account focused on C# .NET development with AI.

The audience is mid-to-senior C# / .NET developers who want to use AI tools to write better code.

A user provided this idea:
"{idea}"

Based on this idea, generate 5 different SPECIFIC titles/topics for {type_desc} that:
{specific_rules}
4. Are distinct from each other (different angles or depths)
5. Are concise (max 60 characters per title)

Return ONLY valid JSON, no markdown:
{{
  "titles": [
    {{
      "rank": 1,
      "title": "specific actionable title (max 60 chars)",
      "description": "brief explanation of what this topic covers (max 100 chars)"
    }},
    ...5 items total
  ]
}}
"""

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    result = json.loads(raw)

    # Ensure exactly 5 titles
    result["titles"] = result.get("titles", [])[:5]
    for i, t in enumerate(result["titles"], 1):
        t["rank"] = i

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
