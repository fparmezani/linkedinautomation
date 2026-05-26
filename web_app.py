"""
dotnet-bot — Interface Web
Uso: python web_app.py
Acesse: http://localhost:5000
"""

import os
import uuid
import threading
from datetime import date
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory, abort, session, redirect, url_for
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)

from content_generator.generator  import load_topics, generate_carousel, mark_topic_used
from carousel_generator.renderer  import render_carousel
from linkedin_publisher.publisher  import publish_carousel, publish_article
from topic_researcher              import research_trending_topic
from article_generator.generator   import generate_article
from article_generator.cover_renderer import render_article_covers
from substack_publisher.publisher  import publish_to_substack
from infographic_generator.generator import generate_infographic
from infographic_generator.renderer  import render_infographics

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dotnet-bot-secret-2025")

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

AUTHOR_NAME   = os.getenv("LINKEDIN_DISPLAY_NAME", "Fernando Parmezani")
AUTHOR_HANDLE = os.getenv("LINKEDIN_HANDLE", "@fparmezani")

APP_USERNAME = os.getenv("APP_USERNAME", "admin")
APP_PASSWORD = os.getenv("APP_PASSWORD", "dotnetbot")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

# jobs[job_id] = { status, step_label, topic, data_pt/en, png_paths_pt/en, ... }
_jobs: dict = {}


# ── Background job ───────────────────────────────────────────────────────────

def _run_generation(job_id: str, topic: dict, template: str = "slide.html"):
    job = _jobs[job_id]
    today = date.today().isoformat()
    out   = OUTPUT_DIR / today

    try:
        job["step_label"] = "Gerando PT-BR com Claude..."
        job["step"] = 1
        data_pt = generate_carousel(topic["topic"], "pt")
        job["data_pt"] = data_pt

        job["step_label"] = "Gerando EN com Claude..."
        job["step"] = 2
        data_en = generate_carousel(topic["topic"], "en")
        job["data_en"] = data_en

        job["step_label"] = "Renderizando slides PT-BR..."
        job["step"] = 3
        png_pt, _ = render_carousel(data_pt, "pt", str(out / "pt"), AUTHOR_NAME, AUTHOR_HANDLE, template=template)
        job["png_paths_pt"] = png_pt

        job["step_label"] = "Renderizando slides EN..."
        job["step"] = 4
        png_en, _ = render_carousel(data_en, "en", str(out / "en"), AUTHOR_NAME, AUTHOR_HANDLE, template=template)
        job["png_paths_en"] = png_en

        job["date"]       = today
        job["step"]       = 5
        job["step_label"] = "Pronto!"
        job["status"]     = "ready"

    except Exception as exc:
        job["status"]     = "error"
        job["step_label"] = str(exc)
        job["error"]      = str(exc)


def _run_article_generation(job_id: str, topic: dict):
    job = _jobs[job_id]
    today = date.today().isoformat()
    out   = OUTPUT_DIR / today / "articles"

    try:
        job["step_label"] = "Gerando artigo PT-BR com Claude..."
        job["step"] = 1
        data_pt = generate_article(topic["topic"], "pt")
        job["data_pt"] = data_pt

        job["step_label"] = "Gerando artigo EN com Claude..."
        job["step"] = 2
        data_en = generate_article(topic["topic"], "en")
        job["data_en"] = data_en

        job["step_label"] = "Renderizando 3 capas PT-BR..."
        job["step"] = 3
        covers_pt = render_article_covers(data_pt, str(out / "pt"), AUTHOR_NAME, AUTHOR_HANDLE)
        job["covers_pt"] = covers_pt

        job["step_label"] = "Renderizando 3 capas EN..."
        job["step"] = 4
        covers_en = render_article_covers(data_en, str(out / "en"), AUTHOR_NAME, AUTHOR_HANDLE)
        job["covers_en"] = covers_en

        job["date"] = today
        job["step"]            = 5
        job["step_label"]      = "Pronto!"
        job["status"]          = "ready"

    except Exception as exc:
        job["status"]     = "error"
        job["step_label"] = str(exc)
        job["error"]      = str(exc)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if session.get("logged_in"):
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == APP_USERNAME and password == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        error = "Usuário ou senha incorretos."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/")
@login_required
def index():
    from flask import make_response
    resp = make_response(render_template("index.html",
                                         author_name=AUTHOR_NAME,
                                         author_handle=AUTHOR_HANDLE))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/api/research", methods=["POST"])
@login_required
def api_research():
    """Pesquisa topicos em alta e sugere o melhor para hoje."""
    def _run(job):
        try:
            data = load_topics()
            # Exclui tanto os já publicados quanto os que já estão na fila
            used      = [t["topic"] for t in data.get("used", [])]
            queued    = [t["topic"] for t in data.get("available", [])]
            all_known = used + queued
            result = research_trending_topic(used_topics=all_known)
            job.update({"status": "done", **result})
        except Exception as exc:
            job.update({"status": "error", "error": str(exc)})

    job_id = uuid.uuid4().hex[:8]
    _jobs[f"research_{job_id}"] = {"status": "running"}
    threading.Thread(target=_run, args=(_jobs[f"research_{job_id}"],), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/research/status/<job_id>")
@login_required
def api_research_status(job_id):
    job = _jobs.get(f"research_{job_id}")
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify(job)


@app.route("/api/topics")
@login_required
def api_topics():
    data = load_topics()
    return jsonify({
        "available":  data["available"],
        "used_count": len(data["used"]),
        "total":      len(data["available"]) + len(data["used"]),
    })


@app.route("/api/generate", methods=["POST"])
@login_required
def api_generate():
    body     = request.get_json() or {}
    topic_id = body.get("topic_id")
    template = body.get("template", "slide.html")
    data     = load_topics()
    available = data["available"]

    if not available:
        return jsonify({"error": "Sem topicos disponíveis. Adicione mais em topics_queue.json"}), 400

    # topic_id=0 significa topico trending passado via topic_name
    topic_name = body.get("topic_name", "")
    if topic_id == 0 and topic_name:
        topic = {"id": 0, "topic": topic_name, "_trending": True}
    else:
        topic = next((t for t in available if t["id"] == topic_id), available[0])

    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "status":      "running",
        "step":        0,
        "step_label":  "Iniciando...",
        "topic":       topic["topic"],
        "topic_id":    topic["id"],
        "template":    template,
        "data_pt":     None,
        "data_en":     None,
        "png_paths_pt": [],
        "png_paths_en": [],
        "date":        None,
        "error":       None,
    }

    threading.Thread(target=_run_generation, args=(job_id, topic, template), daemon=True).start()
    return jsonify({"job_id": job_id, "topic": topic["topic"]})


@app.route("/api/status/<job_id>")
@login_required
def api_status(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404

    result = {
        "status":     job["status"],
        "step":       job.get("step", 0),
        "step_label": job.get("step_label", ""),
        "topic":      job.get("topic", ""),
        "error":      job.get("error"),
    }

    if job["status"] == "ready":
        today = job["date"]
        result["slides_pt"]    = [f"/output/{today}/pt/{Path(p).name}" for p in job["png_paths_pt"]]
        result["slides_en"]    = [f"/output/{today}/en/{Path(p).name}" for p in job["png_paths_en"]]
        result["post_text_pt"] = job["data_pt"]["post_text"]
        result["post_text_en"] = job["data_en"]["post_text"]

    return jsonify(result)


@app.route("/api/publish", methods=["POST"])
@login_required
def api_publish():
    body         = request.get_json() or {}
    job_id       = body.get("job_id")
    post_text_pt = body.get("post_text_pt", "")
    post_text_en = body.get("post_text_en", "")

    job = _jobs.get(job_id)
    if not job or job["status"] != "ready":
        return jsonify({"error": "Job não está pronto para publicação"}), 400

    try:
        title_pt = job["data_pt"]["slides"][0]["title"]
        title_en = job["data_en"]["slides"][0]["title"]

        id_pt = publish_carousel(job["png_paths_pt"], post_text_pt, title_pt)
        id_en = publish_carousel(job["png_paths_en"], post_text_en, title_en)

        mark_topic_used(job["topic_id"])
        job["status"] = "published"

        return jsonify({"id_pt": id_pt, "id_en": id_en})

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/generate-article", methods=["POST"])
@login_required
def api_generate_article():
    body     = request.get_json() or {}
    topic_id = body.get("topic_id")
    data     = load_topics()
    available = data["available"]

    if not available:
        return jsonify({"error": "Sem topicos disponíveis."}), 400

    topic_name = body.get("topic_name", "")
    if topic_id == 0 and topic_name:
        topic = {"id": 0, "topic": topic_name, "_trending": True}
    else:
        topic = next((t for t in available if t["id"] == topic_id), available[0])

    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "status":      "running",
        "step":        0,
        "step_label":  "Iniciando...",
        "topic":       topic["topic"],
        "topic_id":    topic["id"],
        "content_type": "article",
        "data_pt":     None,
        "data_en":     None,
        "cover_pt":    None,
        "cover_en":    None,
        "date":        None,
        "error":       None,
    }

    threading.Thread(target=_run_article_generation, args=(job_id, topic), daemon=True).start()
    return jsonify({"job_id": job_id, "topic": topic["topic"]})


@app.route("/api/status-article/<job_id>")
@login_required
def api_status_article(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404

    result = {
        "status":     job["status"],
        "step":       job.get("step", 0),
        "step_label": job.get("step_label", ""),
        "topic":      job.get("topic", ""),
        "error":      job.get("error"),
    }

    if job["status"] == "ready":
        today = job["date"]
        data_pt = job["data_pt"]
        data_en = job["data_en"]
        result["covers_pt"] = [
            f"/output/{today}/articles/pt/{Path(p).name}" for p in job["covers_pt"]
        ]
        result["covers_en"] = [
            f"/output/{today}/articles/en/{Path(p).name}" for p in job["covers_en"]
        ]
        result["headline_pt"]    = data_pt.get("headline", "")
        result["headline_en"]    = data_en.get("headline", "")
        result["subheadline_pt"] = data_pt.get("subheadline", "")
        result["subheadline_en"] = data_en.get("subheadline", "")
        result["reading_time_pt"] = data_pt.get("reading_time_min", 0)
        result["reading_time_en"] = data_en.get("reading_time_min", 0)
        result["sections_pt"]    = data_pt.get("sections", [])
        result["sections_en"]    = data_en.get("sections", [])
        result["conclusion_pt"]  = data_pt.get("conclusion", "")
        result["conclusion_en"]  = data_en.get("conclusion", "")
        result["post_text_pt"]   = data_pt.get("post_text", "")
        result["post_text_en"]   = data_en.get("post_text", "")
        result["hashtags_pt"]    = data_pt.get("hashtags", [])
        result["hashtags_en"]    = data_en.get("hashtags", [])

    return jsonify(result)


@app.route("/api/publish-article", methods=["POST"])
@login_required
def api_publish_article():
    body         = request.get_json() or {}
    job_id       = body.get("job_id")
    post_text_pt = body.get("post_text_pt", "")
    post_text_en = body.get("post_text_en", "")

    job = _jobs.get(job_id)
    if not job or job["status"] != "ready":
        return jsonify({"error": "Job não está pronto para publicação"}), 400

    try:
        headline_pt = job["data_pt"]["headline"]
        headline_en = job["data_en"]["headline"]

        # 1. Publica no Substack e obtém URLs reais
        substack_url_pt = publish_to_substack(job["data_pt"], job["cover_pt"])
        substack_url_en = publish_to_substack(job["data_en"], job["cover_en"])
        job["substack_url_pt"] = substack_url_pt
        job["substack_url_en"] = substack_url_en

        # 2. Publica no LinkedIn com o link do Substack
        full_text_pt = f"{post_text_pt}\n\n🔗 Leia o artigo completo: {substack_url_pt}"
        full_text_en = f"{post_text_en}\n\n🔗 Read the full article: {substack_url_en}"

        id_pt = publish_article(job["cover_pt"], full_text_pt, headline_pt)
        id_en = publish_article(job["cover_en"], full_text_en, headline_en)

        mark_topic_used(job["topic_id"])
        job["status"] = "published"

        return jsonify({
            "id_pt":            id_pt,
            "id_en":            id_en,
            "substack_url_pt":  substack_url_pt,
            "substack_url_en":  substack_url_en,
        })

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def _run_infographic_generation(job_id: str, topic: dict):
    job = _jobs[job_id]
    today = date.today().isoformat()
    out = OUTPUT_DIR / today / "infographics"

    try:
        job["step_label"] = "Gerando infográfico PT-BR com Claude..."
        job["step"] = 1
        data_pt = generate_infographic(topic["topic"], "pt")
        job["data_pt"] = data_pt

        job["step_label"] = "Gerando infográfico EN com Claude..."
        job["step"] = 2
        data_en = generate_infographic(topic["topic"], "en")
        job["data_en"] = data_en

        job["step_label"] = "Renderizando 3 formatos PT-BR..."
        job["step"] = 3
        imgs_pt = render_infographics(data_pt, str(out / "pt"), AUTHOR_NAME, AUTHOR_HANDLE)
        job["images_pt"] = imgs_pt

        job["step_label"] = "Renderizando 3 formatos EN..."
        job["step"] = 4
        imgs_en = render_infographics(data_en, str(out / "en"), AUTHOR_NAME, AUTHOR_HANDLE)
        job["images_en"] = imgs_en

        job["date"] = today
        job["step"] = 5
        job["step_label"] = "Pronto!"
        job["status"] = "ready"

    except Exception as exc:
        job["status"] = "error"
        job["step_label"] = str(exc)
        job["error"] = str(exc)


@app.route("/api/generate-infographic", methods=["POST"])
@login_required
def api_generate_infographic():
    body = request.get_json() or {}
    topic_id = body.get("topic_id")
    data = load_topics()
    available = data["available"]

    if not available:
        return jsonify({"error": "Sem topicos disponíveis."}), 400

    topic_name = body.get("topic_name", "")
    if topic_id == 0 and topic_name:
        topic = {"id": 0, "topic": topic_name, "_trending": True}
    else:
        topic = next((t for t in available if t["id"] == topic_id), available[0])

    job_id = uuid.uuid4().hex[:8]
    _jobs[job_id] = {
        "status": "running",
        "step": 0,
        "step_label": "Iniciando...",
        "topic": topic["topic"],
        "topic_id": topic["id"],
        "content_type": "infographic",
        "data_pt": None,
        "data_en": None,
        "images_pt": None,
        "images_en": None,
        "date": None,
        "error": None,
    }

    threading.Thread(target=_run_infographic_generation, args=(job_id, topic), daemon=True).start()
    return jsonify({"job_id": job_id, "topic": topic["topic"]})


@app.route("/api/status-infographic/<job_id>")
@login_required
def api_status_infographic(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404

    result = {
        "status": job["status"],
        "step": job.get("step", 0),
        "step_label": job.get("step_label", ""),
        "topic": job.get("topic", ""),
        "error": job.get("error"),
    }

    if job["status"] == "ready":
        today = job["date"]
        data_pt = job["data_pt"]
        data_en = job["data_en"]
        result["images_pt"] = [
            f"/output/{today}/infographics/pt/{Path(p).name}" for p in job["images_pt"]
        ]
        result["images_en"] = [
            f"/output/{today}/infographics/en/{Path(p).name}" for p in job["images_en"]
        ]
        result["title_pt"] = data_pt.get("title", "")
        result["title_en"] = data_en.get("title", "")
        result["hashtags_pt"] = data_pt.get("hashtags", [])
        result["hashtags_en"] = data_en.get("hashtags", [])
        result["post_text_pt"] = f"{data_pt.get('title', '')}\n\n{data_pt.get('subtitle', '')}\n\n{data_pt.get('footer_cta', '')}\n\n{' '.join('#' + h for h in data_pt.get('hashtags', []))}"
        result["post_text_en"] = f"{data_en.get('title', '')}\n\n{data_en.get('subtitle', '')}\n\n{data_en.get('footer_cta', '')}\n\n{' '.join('#' + h for h in data_en.get('hashtags', []))}"

    return jsonify(result)


@app.route("/api/publish-infographic", methods=["POST"])
@login_required
def api_publish_infographic():
    body = request.get_json() or {}
    job_id = body.get("job_id")
    post_text_pt = body.get("post_text_pt", "")
    post_text_en = body.get("post_text_en", "")

    job = _jobs.get(job_id)
    if not job or job["status"] != "ready":
        return jsonify({"error": "Job não está pronto para publicação"}), 400

    try:
        fmt_idx = int(body.get("format_index", 1))
        fmt_idx = max(0, min(fmt_idx, len(job["images_pt"]) - 1))
        img_pt = job["images_pt"][fmt_idx]
        img_en = job["images_en"][fmt_idx]

        id_pt = publish_article(img_pt, post_text_pt, job["data_pt"]["title"])
        id_en = publish_article(img_en, post_text_en, job["data_en"]["title"])

        mark_topic_used(job["topic_id"])
        job["status"] = "published"

        return jsonify({"id_pt": id_pt, "id_en": id_en})

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/output/<path:filename>")
def serve_output(filename):
    path = OUTPUT_DIR / filename
    if not path.exists():
        abort(404)
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/template-preview/<template_id>")
def serve_template_preview(template_id):
    """Serve template preview images."""
    template_map = {
        "original": "template_previews/template_original_cover.png",
        "minimal":  "template_previews/template_minimal_cover.png",
        "card":     "template_previews/template_card_cover.png",
    }
    if template_id not in template_map:
        abort(404)
    path = BASE_DIR / template_map[template_id]
    if not path.exists():
        abort(404)
    return send_from_directory(path.parent, path.name)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    host = "0.0.0.0" if os.getenv("RENDER") else "127.0.0.1"
    print(f"\n  dotnet-bot rodando em http://{host}:{port}\n")
    app.run(debug=False, host=host, port=port, threaded=True)
