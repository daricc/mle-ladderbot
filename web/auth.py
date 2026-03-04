"""Discord OAuth and session handling for Crossbar League site."""
import os
import secrets
import urllib.parse
from typing import Optional

import httpx
from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer

DISCORD_API = "https://discord.com/api/v10"
DISCORD_OAUTH = "https://discord.com/api/oauth2"

SESSION_COOKIE = "crossbar_session"
SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days


def _serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("SESSION_SECRET") or os.getenv("DISCORD_CLIENT_SECRET") or "dev-secret-change-me"
    return URLSafeTimedSerializer(secret, salt="crossbar-session", signer_kwargs={"digest_method": "sha256"})


def _auth_url(redirect_uri: str) -> str:
    client_id = os.getenv("DISCORD_CLIENT_ID")
    if not client_id:
        raise HTTPException(503, "Discord OAuth not configured")
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }
    return f"{DISCORD_OAUTH}/authorize?{urllib.parse.urlencode(params)}", state


async def discord_oauth_callback(code: str, redirect_uri: str) -> dict:
    """Exchange code for Discord user info. Returns {id, username, discriminator, avatar}."""
    client_id = os.getenv("DISCORD_CLIENT_ID")
    client_secret = os.getenv("DISCORD_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(503, "Discord OAuth not configured")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            f"{DISCORD_OAUTH}/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        if token_resp.status_code != 200:
            err_body = token_resp.text[:200] if token_resp.text else ""
            raise HTTPException(400, f"Discord auth failed: {err_body or token_resp.status_code}")

        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(400, "No access token")

        user_resp = await client.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if user_resp.status_code != 200:
            raise HTTPException(400, "Failed to fetch Discord user")

        user = user_resp.json()
        return {
            "id": str(user.get("id", "")),
            "username": user.get("username", ""),
            "discriminator": user.get("discriminator", "0"),
            "avatar": user.get("avatar"),
            "display_name": user.get("global_name") or user.get("username", ""),
        }


def set_session(response: Response, discord_id: str, display_name: str) -> None:
    """Set signed session cookie."""
    ser = _serializer()
    payload = {"d": discord_id, "n": display_name[:100]}
    token = ser.dumps(payload)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=os.getenv("SITE_URL", "").startswith("https://"),
    )


def get_session(request: Request) -> Optional[dict]:
    """Get session payload from cookie. Returns {d: discord_id, n: display_name} or None."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        ser = _serializer()
        return ser.loads(token, max_age=SESSION_MAX_AGE)
    except BadSignature:
        return None


def clear_session(response: Response) -> None:
    """Clear session cookie."""
    response.delete_cookie(SESSION_COOKIE)
