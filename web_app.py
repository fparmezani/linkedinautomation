"""
dotnet-bot — Interface Web
Uso: python web_app.py
Acesse: http://localhost:5000
"""

import os
import uuid
import threading
from datetime import date
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory, abort
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)

from content_generator.generator  import load_topics, generate_carousel, mark_topic_used
from carousel_generator.renderer  import render_carousel
from linkedin_publisher.publisher import publish_carousel
from topic_researcher             import research_trending_topic

app = Flask(__name__)

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

AUTHOR_NAME   = os.getenv("LINKEDIN_DISPLAY_NAME", "Fernando Parmezani")
AUTHOR_HANDLE = os.getenv("LINKEDIN_HANDLE", "@fparmezani")

# jobs[job_id] = { status, step_label, topic, data_pt/en, png_paths_pt/en, ... }
_jobs: dict = {}


# ── Background job ───────────────────────────────────────────────────────────

def _run_generation(job_id: str, topic: dict):
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
        png_pt, _ = render_carousel(data_pt, "pt", str(out / "pt"), AUTHOR_NAME, AUTHOR_HANDLE)
        job["png_paths_pt"] = png_pt

        job["step_label"] = "Renderizando slides EN..."
        job["step"] = 4
        png_en, _ = render_carousel(data_en, "en", str(out / "en"), AUTHOR_NAME, AUTHOR_HANDLE)
        job["png_paths_en"] = png_en

        job["date"]       = today
        job["step"]       = 5
        job["step_label"] = "Pronto!"
        job["status"]     = "ready"

    except Exception as exc:
        job["status"]     = "error"
        job["step_label"] = str(exc)
        job["error"]      = str(exc)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
                           author_name=AUTHOR_NAME,
                           author_handle=AUTHOR_HANDLE)


@app.route("/api/research", methods=["POST"])
def api_research():
    """Pesquisa topicos em alta e sugere o melhor para hoje."""
    def _run(job):
        try:
            data = load_topics()
            used = [t["topic"] for t in data.get("used", [])]
            result = research_trending_topic(used_topics=used)
            job.update({"status": "done", **result})
        except Exception as exc:
            job.update({"status": "error", "error": str(exc)})

    job_id = uuid.uuid4().hex[:8]
    _jobs[f"research_{job_id}"] = {"status": "running"}
    threading.Thread(target=_run, args=(_jobs[f"research_{job_id}"],), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/research/status/<job_id>")
def api_research_status(job_id):
    job = _jobs.get(f"research_{job_id}")
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify(job)


@app.route("/api/topics")
def api_topics():
    data = load_topics()
    return jsonify({
        "available":  data["available"],
        "used_count": len(data["used"]),
        "total":      len(data["available"]) + len(data["used"]),
    })


@app.route("/api/generate", methods=["POST"])
def api_generate():
    body     = request.get_json() or {}
    topic_id = body.get("topic_id")
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
        "data_pt":     None,
        "data_en":     None,
        "png_paths_pt": [],
        "png_paths_en": [],
        "date":        None,
        "error":       None,
    }

    threading.Thread(target=_run_generation, args=(job_id, topic), daemon=True).start()
    return jsonify({"job_id": job_id, "topic": topic["topic"]})


@app.route("/api/status/<job_id>")
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


@app.route("/output/<path:filename>")
def serve_output(filename):
    path = OUTPUT_DIR / filename
    if not path.exists():
        abort(404)
    return send_from_directory(OUTPUT_DIR, filename)


if __name__ == "__main__":
    print("\n  dotnet-bot rodando em http://localhost:5000\n")
    app.run(debug=False, host="127.0.0.1", port=5000, threaded=True)
