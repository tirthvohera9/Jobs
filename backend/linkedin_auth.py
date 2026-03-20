"""
LinkedIn OAuth 2.0 authentication module.

Flow:
  1. GET /api/auth/linkedin/login   → redirects user to LinkedIn OAuth page
  2. LinkedIn redirects back to /api/auth/linkedin/callback?code=...
  3. Backend exchanges code for access token
  4. Backend fetches user profile from LinkedIn API
  5. Returns token + profile to frontend (via redirect with query params or JSON)

Required environment variables:
  LINKEDIN_CLIENT_ID      — from your LinkedIn Developer App
  LINKEDIN_CLIENT_SECRET  — from your LinkedIn Developer App
  FRONTEND_URL            — base URL of the frontend (for redirect after OAuth)
  APP_SECRET_KEY          — secret for signing session tokens

LinkedIn Developer App setup:
  https://www.linkedin.com/developers/apps/new
  Required OAuth 2.0 scopes: openid, profile, email
  Add redirect URL: http://localhost:8000/api/auth/linkedin/callback
"""

import os
import time
import secrets
import hashlib
import base64
import logging
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
REDIRECT_URI = os.getenv(
    "LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/auth/linkedin/callback"
)

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_PROFILE_URL = "https://api.linkedin.com/v2/userinfo"  # OpenID Connect userinfo

# In-memory state store (use Redis/DB in production)
_state_store: dict[str, float] = {}
STATE_TTL = 600  # 10 minutes


def generate_login_url() -> tuple[str, str]:
    """
    Generate the LinkedIn OAuth authorization URL and a CSRF state token.
    Returns (url, state).
    """
    if not LINKEDIN_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="LinkedIn OAuth not configured. Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET.",
        )

    state = secrets.token_urlsafe(32)
    _state_store[state] = time.time()

    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email",
        "state": state,
    }
    url = f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"
    return url, state


def _cleanup_expired_states():
    now = time.time()
    expired = [k for k, ts in _state_store.items() if now - ts > STATE_TTL]
    for k in expired:
        del _state_store[k]


async def exchange_code_for_token(code: str, state: str) -> dict:
    """
    Exchange OAuth authorization code for an access token.
    Returns the token response dict.
    """
    _cleanup_expired_states()

    if state not in _state_store:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")
    del _state_store[state]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            LINKEDIN_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )

    if resp.status_code != 200:
        logger.error("Token exchange failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="Failed to obtain LinkedIn access token.")

    return resp.json()


async def fetch_linkedin_profile(access_token: str) -> dict:
    """
    Fetch the authenticated user's LinkedIn profile using OpenID Connect userinfo.
    Returns a dict with: sub, name, given_name, family_name, email, picture, locale.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            LINKEDIN_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )

    if resp.status_code != 200:
        logger.error("Profile fetch failed: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=502, detail="Failed to fetch LinkedIn profile.")

    return resp.json()


async def get_linkedin_profile_and_token(code: str, state: str) -> dict:
    """
    Full OAuth callback handler: exchange code → token → profile.
    Returns combined dict with access_token and profile fields.
    """
    token_data = await exchange_code_for_token(code, state)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="No access token in LinkedIn response.")

    profile = await fetch_linkedin_profile(access_token)

    return {
        "access_token": access_token,
        "expires_in": token_data.get("expires_in"),
        "profile": {
            "id": profile.get("sub"),
            "name": profile.get("name"),
            "given_name": profile.get("given_name"),
            "family_name": profile.get("family_name"),
            "email": profile.get("email"),
            "picture": profile.get("picture"),
        },
    }
