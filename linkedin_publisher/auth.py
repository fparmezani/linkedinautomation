import os
import re
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

ENV_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))


def _update_env(key: str, value: str):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    pattern = rf"^{re.escape(key)}=.*$"
    new_content = re.sub(pattern, f"{key}={value}", content, flags=re.MULTILINE)
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


def get_access_token() -> str:
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "LINKEDIN_ACCESS_TOKEN not found in .env.\n"
            "Run: python setup_auth.py"
        )
    return token


def refresh_token_if_needed():
    """
    LinkedIn tokens last ~60 days. If LINKEDIN_REFRESH_TOKEN is set,
    attempts to exchange it for a new access token and updates .env.
    Call this at the start of the daily run as a precaution.
    """
    refresh = os.getenv("LINKEDIN_REFRESH_TOKEN", "").strip()
    if not refresh:
        return  # no refresh token available, skip

    client_id     = os.getenv("LINKEDIN_CLIENT_ID", "")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "")

    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type":    "refresh_token",
            "refresh_token": refresh,
            "client_id":     client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.ok:
        tokens = resp.json()
        _update_env("LINKEDIN_ACCESS_TOKEN",  tokens.get("access_token", ""))
        if tokens.get("refresh_token"):
            _update_env("LINKEDIN_REFRESH_TOKEN", tokens["refresh_token"])
        # reload env after update
        load_dotenv(override=True)
