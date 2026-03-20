"""
LinkedIn OAuth 2.0 authentication module.

Flow:
  1. GET /api/auth/linkedin/login   → redirects user to LinkedIn OAuth page
  2. LinkedIn redirects back to /api/auth/linkedin/callback?code=...
  3. Backend exchanges code for access token
  4. Backend fetches user profile from LinkedIn API
  5. Redirects to frontend with token + profile as query params

Stateless state token:
  Instead of an in-memory dict (which breaks on serverless — each request is a
  new process), we encode the timestamp into the state param and sign it with
  APP_SECRET_KEY using HMAC-SHA256. No server-side storage required.

Required environment variables (set in Vercel Dashboard → Settings → Environment Variables):
  LINKEDIN_CLIENT_ID      — from your LinkedIn Developer App
  LINKEDIN_CLIENT_SECRET  — from your LinkedIn Developer App
  APP_SECRET_KEY          — any random secret string (for signing state tokens)

Auto-detected from Vercel (no manual setup needed):
  FRONTEND_URL            — derived from VERCEL_PROJECT_PRODUCTION_URL or VERCEL_URL
  LINKEDIN_REDIRECT_URI   — same base URL + /api/auth/linkedin/callback

LinkedIn Developer App setup:
  https://www.linkedin.com/developers/apps/new
  Required OAuth 2.0 scopes: openid, profile, email
  Add redirect URL: https://<your-vercel-domain>/api/auth/linkedin/callback
"""

import os
import time
import hmac
import hashlib
import base64
import logging
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

LINKEDIN_CLIENT_ID     = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
APP_SECRET_KEY         = os.getenv("APP_SECRET_KEY", "change-me-in-production")

# Auto-detect the base URL from Vercel environment variables.
# VERCEL_PROJECT_PRODUCTION_URL is the stable production URL (no https:// prefix).
# VERCEL_URL is the per-deployment URL (also no prefix). Falls back to localhost.
_vercel_prod = os.getenv("VERCEL_PROJECT_PRODUCTION_URL", "")
_vercel_any  = os.getenv("VERCEL_URL", "")
_base_host   = _vercel_prod or _vercel_any

FRONTEND_URL  = os.getenv(
    "FRONTEND_URL",
    f"https://{_base_host}" if _base_host else "http://localhost:5173",
)
REDIRECT_URI  = os.getenv(
    "LINKEDIN_REDIRECT_URI",
    f"https://{_base_host}/api/auth/linkedin/callback" if _base_host else "http://localhost:8000/api/auth/linkedin/callback",
)

LINKEDIN_AUTH_URL    = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL   = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_PROFILE_URL = "https://api.linkedin.com/v2/userinfo"

STATE_TTL = 600  # 10 minutes


# ── Stateless HMAC state tokens ───────────────────────────────────────────────

def _make_state() -> str:
    """
    Create a tamper-proof state token containing the current timestamp.
    Format: base64(timestamp) . hmac_signature[:16]
    No server-side storage needed — the signature proves authenticity.
    """
    ts = str(int(time.time())).encode()
    ts_b64 = base64.urlsafe_b64encode(ts).decode().rstrip("=")
    sig = hmac.new(APP_SECRET_KEY.encode(), ts_b64.encode(), hashlib.sha256).hexdigest()[:20]
    return f"{ts_b64}.{sig}"


def _verify_state(state: str) -> bool:
    """Verify the state token was issued by us and is not expired."""
    try:
        ts_b64, sig = state.rsplit(".", 1)
        expected = hmac.new(APP_SECRET_KEY.encode(), ts_b64.encode(), hashlib.sha256).hexdigest()[:20]
        if not hmac.compare_digest(sig, expected):
            return False
        # Pad base64 and decode timestamp
        padding = "=" * (-len(ts_b64) % 4)
        timestamp = int(base64.urlsafe_b64decode(ts_b64 + padding).decode())
        return (time.time() - timestamp) < STATE_TTL
    except Exception:
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def generate_login_url() -> tuple[str, str]:
    """
    Generate the LinkedIn OAuth authorization URL.
    Returns (url, state).
    """
    if not LINKEDIN_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail=(
                "LinkedIn OAuth is not configured. "
                "Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in Vercel environment variables."
            ),
        )

    state = _make_state()
    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email",
        "state": state,
    }
    url = f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"
    return url, state


async def exchange_code_for_token(code: str, state: str) -> dict:
    """Exchange OAuth authorization code for an access token."""
    if not _verify_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state. Please try signing in again.")

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
    """Fetch user profile via OpenID Connect userinfo endpoint."""
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
    """Full OAuth callback: exchange code → token → profile."""
    token_data = await exchange_code_for_token(code, state)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="No access token in LinkedIn response.")

    profile = await fetch_linkedin_profile(access_token)

    return {
        "access_token": access_token,
        "expires_in": token_data.get("expires_in"),
        "profile": {
            "id":          profile.get("sub"),
            "name":        profile.get("name"),
            "given_name":  profile.get("given_name"),
            "family_name": profile.get("family_name"),
            "email":       profile.get("email"),
            "picture":     profile.get("picture"),
        },
    }
