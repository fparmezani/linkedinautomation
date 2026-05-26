"""
Substack publisher — publica artigos via API não oficial do Substack.
Requer: SUBSTACK_EMAIL, SUBSTACK_PASSWORD, SUBSTACK_URL no .env
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

_session = None


def _get_session() -> requests.Session:
    """Retorna sessão autenticada usando cookie de sessão do Substack."""
    global _session
    if _session:
        return _session

    cookie = os.getenv("SUBSTACK_SESSION", "").strip()
    if not cookie:
        raise RuntimeError("SUBSTACK_SESSION não configurado no .env")

    sess = requests.Session()
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
    })
    sess.cookies.set("substack.sid", cookie, domain="substack.com")

    _session = sess
    return _session


def _article_to_html(article_data: dict) -> str:
    """Converte artigo gerado para HTML rico aceito pelo Substack."""
    parts = []

    subheadline = article_data.get("subheadline", "")
    if subheadline:
        parts.append(f'<p><em>{subheadline}</em></p>')

    for section in article_data.get("sections", []):
        heading = section.get("heading", "")
        body    = section.get("body", "")
        code    = section.get("code_block")
        lang    = section.get("code_language", "csharp")

        if heading:
            parts.append(f"<h2>{heading}</h2>")

        if body:
            for para in body.split("\n\n"):
                para = para.strip()
                if para:
                    para_html = para.replace("\n", "<br>")
                    parts.append(f"<p>{para_html}</p>")

        if code:
            escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            parts.append(f'<pre><code class="language-{lang}">{escaped}</code></pre>')

    conclusion = article_data.get("conclusion", "")
    if conclusion:
        parts.append("<h2>Conclusão</h2>")
        for para in conclusion.split("\n\n"):
            if para.strip():
                parts.append(f"<p>{para.strip()}</p>")

    cta = article_data.get("cta", "")
    if cta:
        parts.append(f"<p><strong>{cta}</strong></p>")

    hashtags = article_data.get("hashtags", [])
    if hashtags:
        tags = " ".join(f"#{h}" for h in hashtags)
        parts.append(f"<p>{tags}</p>")

    return "\n".join(parts)


def _upload_cover_image(cover_png_path: str, sess: requests.Session,
                        substack_url: str) -> str | None:
    """Faz upload da imagem de capa e retorna a URL pública."""
    try:
        with open(cover_png_path, "rb") as f:
            resp = sess.post(
                f"{substack_url}/api/v1/image",
                files={"image": ("cover.png", f, "image/png")},
                headers={k: v for k, v in sess.headers.items() if k != "Content-Type"},
            )
        if resp.ok:
            return resp.json().get("url")
    except Exception as e:
        print(f"    Aviso: falha no upload da imagem — {e}")
    return None


def publish_to_substack(article_data: dict, cover_png_path: str) -> str:
    """
    Publica artigo no Substack e retorna a URL pública do post.
    """
    substack_url = os.getenv("SUBSTACK_URL", "").rstrip("/")
    if not substack_url:
        raise RuntimeError("SUBSTACK_URL não configurado no .env")

    sess = _get_session()

    # 1. Upload da imagem de capa
    print("    Uploading cover to Substack...", end=" ", flush=True)
    cover_url = _upload_cover_image(cover_png_path, sess, substack_url)
    print("ok" if cover_url else "sem imagem")

    # 2. Converte conteúdo para HTML
    html_body  = _article_to_html(article_data)
    headline   = article_data.get("headline", article_data.get("topic", ""))
    subtitle   = article_data.get("subheadline", "")

    # 3. Cria o draft
    print("    Creating Substack draft...", end=" ", flush=True)
    draft_payload = {
        "draft_title":       headline,
        "draft_subtitle":    subtitle,
        "draft_body":        html_body,
        "draft_byline":      "",
        "section_chosen":    None,
        "audience":          "everyone",
        "type":              "newsletter",
    }
    if cover_url:
        draft_payload["cover_image"] = cover_url

    resp = sess.post(
        f"{substack_url}/api/v1/drafts",
        json=draft_payload,
    )

    if not resp.ok:
        raise RuntimeError(
            f"Erro ao criar draft ({resp.status_code}): {resp.text[:300]}"
        )

    draft = resp.json()
    draft_id = draft.get("id")
    print(f"ok (id: {draft_id})")

    # 4. Publica o draft
    print("    Publishing Substack post...", end=" ", flush=True)
    pub_resp = sess.post(
        f"{substack_url}/api/v1/drafts/{draft_id}/publish",
        json={"audience": "everyone", "send": True},
    )

    if not pub_resp.ok:
        raise RuntimeError(
            f"Erro ao publicar ({pub_resp.status_code}): {pub_resp.text[:300]}"
        )

    pub_data = pub_resp.json()
    slug     = pub_data.get("slug") or draft.get("slug") or str(draft_id)
    post_url = f"{substack_url}/p/{slug}"
    print(f"ok → {post_url}")

    return post_url
