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
