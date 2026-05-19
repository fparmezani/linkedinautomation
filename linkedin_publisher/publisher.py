import os
import requests
from dotenv import load_dotenv
from .auth import get_access_token

load_dotenv(override=True)

API_BASE = "https://api.linkedin.com"


def _register_image(author_urn: str, token: str) -> tuple:
    resp = requests.post(
        f"{API_BASE}/v2/assets?action=registerUpload",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"registerUploadRequest": {
            "owner": author_urn,
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "serviceRelationships": [{"relationshipType": "OWNER",
                                       "identifier": "urn:li:userGeneratedContent"}],
            "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"],
        }},
    )
    resp.raise_for_status()
    value = resp.json()["value"]
    upload_url = value["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = value["asset"]
    return upload_url, asset_urn


def _upload_image(png_path: str, upload_url: str, token: str):
    with open(png_path, "rb") as f:
        data = f.read()
    resp = requests.put(
        upload_url,
        headers={"Authorization": f"Bearer {token}", "media-type-family": "STILLIMAGE"},
        data=data,
    )
    resp.raise_for_status()


def _create_post(author_urn: str, commentary: str,
                 asset_urns: list, title: str, token: str) -> str:
    media = [
        {
            "status": "READY",
            "description": {"text": f"Slide {i + 1}"},
            "media": urn,
            "title": {"text": f"{title} ({i + 1}/{len(asset_urns)})"},
        }
        for i, urn in enumerate(asset_urns)
    ]
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": commentary},
                "shareMediaCategory": "IMAGE",
                "media": media,
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }
    resp = requests.post(
        f"{API_BASE}/v2/ugcPosts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
    )
    resp.raise_for_status()
    return resp.json().get("id", "unknown")


def _register_cover_image(author_urn: str, token: str) -> tuple:
    """Register image specifically for article cover (different recipe)."""
    resp = requests.post(
        f"{API_BASE}/v2/assets?action=registerUpload",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"registerUploadRequest": {
            "owner": author_urn,
            "recipes": ["urn:li:digitalmediaRecipe:article-cover-image"],
            "serviceRelationships": [{"relationshipType": "OWNER",
                                       "identifier": "urn:li:userGeneratedContent"}],
            "supportedUploadMechanism": ["SYNCHRONOUS_UPLOAD"],
        }},
    )
    # Fall back to feedshare recipe if article-cover not available
    if not resp.ok:
        return _register_image(author_urn, token)
    value = resp.json()["value"]
    upload_url = value["uploadMechanism"][
        "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
    ]["uploadUrl"]
    asset_urn = value["asset"]
    return upload_url, asset_urn


def _article_data_to_html(article_data: dict) -> str:
    """Convert article data dict to HTML content for LinkedIn native article."""
    html_parts = []

    # Subheadline as intro
    subheadline = article_data.get("subheadline", "")
    if subheadline:
        html_parts.append(f"<p><em>{subheadline}</em></p>")

    # Sections
    for section in article_data.get("sections", []):
        heading = section.get("heading", "")
        body    = section.get("body", "")
        code    = section.get("code_block")

        if heading:
            html_parts.append(f"<h2>{heading}</h2>")

        # Convert body paragraphs (split by double newline)
        if body:
            paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
            for p in paragraphs:
                # Convert single newlines to <br>
                p_html = p.replace("\n", "<br>")
                html_parts.append(f"<p>{p_html}</p>")

        if code:
            # LinkedIn articles support <pre> blocks
            html_parts.append(f"<pre>{code}</pre>")

    # Conclusion
    conclusion = article_data.get("conclusion", "")
    if conclusion:
        html_parts.append("<h2>Conclusão</h2>")
        for p in conclusion.split("\n\n"):
            if p.strip():
                html_parts.append(f"<p>{p.strip()}</p>")

    # CTA
    cta = article_data.get("cta", "")
    if cta:
        html_parts.append(f"<p><strong>{cta}</strong></p>")

    # Hashtags
    hashtags = article_data.get("hashtags", [])
    if hashtags:
        tags_str = " ".join(f"#{h}" for h in hashtags)
        html_parts.append(f"<p>{tags_str}</p>")

    return "\n".join(html_parts)


def _create_native_article(author_urn: str, title: str, html_content: str,
                            cover_asset_urn: str, token: str) -> str:
    """Publish a native LinkedIn Article (Pulse) via /v2/articles."""
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "title": title,
        "content": html_content,
        "coverImage": {
            "croppedImage": {
                "com.linkedin.digitalmedia.mediaartifact.StillImage": {
                    "storageSize": {"height": 627, "width": 1200},
                    "storageAspectRatio": {
                        "formatted": "1.91:1",
                        "widthAspect": 1.91,
                        "heightAspect": 1,
                    },
                },
                "mediaUrn": cover_asset_urn,
            },
            "originalImage": cover_asset_urn,
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }
    resp = requests.post(
        f"{API_BASE}/v2/articles",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        json=payload,
    )
    if not resp.ok:
        raise RuntimeError(
            f"LinkedIn /v2/articles error {resp.status_code}: {resp.text[:400]}"
        )
    return resp.headers.get("x-restli-id") or resp.json().get("id", "unknown")


def publish_article(cover_png_path: str, post_text: str, headline: str) -> str:
    """Upload cover image and publish article post with link on LinkedIn."""
    author_urn = os.getenv("LINKEDIN_AUTHOR_URN", "").strip()
    if not author_urn:
        raise RuntimeError("LINKEDIN_AUTHOR_URN not set in .env")

    token = get_access_token()

    print("    Uploading cover image...", end=" ", flush=True)
    upload_url, asset_urn = _register_image(author_urn, token)
    _upload_image(cover_png_path, upload_url, token)
    print("ok")

    print("    Publishing post with article link...", end=" ", flush=True)
    payload = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "IMAGE",
                "media": [{
                    "status": "READY",
                    "description": {"text": headline},
                    "media": asset_urn,
                    "title": {"text": headline},
                }],
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    resp = requests.post(
        f"{API_BASE}/v2/ugcPosts",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=payload,
    )
    resp.raise_for_status()
    post_id = resp.json().get("id", "unknown")
    print("ok")
    return post_id


def publish_carousel(png_paths: list, post_text: str, title: str) -> str:
    author_urn = os.getenv("LINKEDIN_AUTHOR_URN", "").strip()
    if not author_urn:
        raise RuntimeError("LINKEDIN_AUTHOR_URN not set in .env")

    token = get_access_token()
    asset_urns = []

    for i, path in enumerate(png_paths):
        print(f"    slide {i + 1}/{len(png_paths)}...", end=" ", flush=True)
        upload_url, asset_urn = _register_image(author_urn, token)
        _upload_image(path, upload_url, token)
        asset_urns.append(asset_urn)
        print("ok")

    print("    Creating post...", end=" ", flush=True)
    post_id = _create_post(author_urn, post_text, asset_urns, title, token)
    print("ok")
    return post_id
