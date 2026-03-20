"""
FastAPI backend for LinkedIn Job Finder.

Endpoints:
  POST /api/parse-resume               — upload resume, returns extracted info + jobs
  GET  /api/search-jobs                — search jobs by keyword and location
  GET  /api/auth/linkedin/login        — start LinkedIn OAuth flow
  GET  /api/auth/linkedin/callback     — OAuth callback, returns token + profile
  GET  /api/auth/linkedin/profile      — fetch profile with existing token
  GET  /api/health                     — health check
"""

import logging
import os
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from resume_parser import parse_resume
from linkedin_scraper import search_jobs
from linkedin_auth import (
    generate_login_url,
    get_linkedin_profile_and_token,
    fetch_linkedin_profile,
    FRONTEND_URL,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="LinkedIn Job Finder API",
    description="Upload your resume and find matching LinkedIn jobs.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE_MB = 5


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── LinkedIn OAuth ───────────────────────────────────────────────────────────

@app.get("/api/auth/linkedin/login")
def linkedin_login():
    """Redirect the user to LinkedIn's OAuth authorization page."""
    auth_url, state = generate_login_url()
    return RedirectResponse(url=auth_url)


@app.get("/api/auth/linkedin/callback")
async def linkedin_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
):
    """
    LinkedIn redirects here after the user authorizes (or denies) the app.
    On success: redirects to frontend with access_token and profile info.
    On failure: redirects to frontend with error info.
    """
    if error:
        redirect_url = (
            f"{FRONTEND_URL}?auth_error={error}"
            f"&error_description={error_description or ''}"
        )
        return RedirectResponse(url=redirect_url)

    if not code or not state:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=missing_params")

    try:
        auth_data = await get_linkedin_profile_and_token(code, state)
    except HTTPException as exc:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error={exc.detail}")

    # Pass token and profile back to the SPA via query params
    # (In production, prefer server-side session cookies instead)
    from urllib.parse import urlencode, quote
    import json

    profile = auth_data["profile"]
    params = urlencode({
        "access_token": auth_data["access_token"],
        "linkedin_name": profile.get("name", ""),
        "linkedin_email": profile.get("email", ""),
        "linkedin_picture": profile.get("picture", ""),
    })
    return RedirectResponse(url=f"{FRONTEND_URL}?{params}")


@app.get("/api/auth/linkedin/profile")
async def get_profile(authorization: Optional[str] = Header(default=None)):
    """Return the LinkedIn profile for an existing Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    token = authorization.split(" ", 1)[1]
    profile = await fetch_linkedin_profile(token)
    return profile


# ── Resume upload + job search ───────────────────────────────────────────────

@app.post("/api/parse-resume")
async def parse_resume_endpoint(
    file: UploadFile = File(...),
    location: Optional[str] = Query(default="", description="Job location filter"),
    max_results: int = Query(default=20, ge=1, le=50),
    fetch_descriptions: bool = Query(default=False),
    linkedin_name: Optional[str] = Query(default=None),
):
    """
    Upload a resume (PDF / DOCX / TXT) and receive extracted info + LinkedIn jobs.
    Optionally pass linkedin_name from the OAuth flow to enrich the response.
    """
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload a PDF, DOCX, or TXT file.",
        )

    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB.",
        )

    try:
        resume_data = parse_resume(file_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Resume parsing failed")
        raise HTTPException(status_code=500, detail="Failed to parse resume.")

    # Prefer the LinkedIn account name if provided
    if linkedin_name and not resume_data.get("name"):
        resume_data["name"] = linkedin_name

    try:
        jobs = search_jobs(
            keywords=resume_data["primary_query"],
            location=location,
            max_results=max_results,
            fetch_descriptions=fetch_descriptions,
        )
    except Exception:
        logger.exception("LinkedIn search failed")
        jobs = []

    return {
        "resume": {
            "name": resume_data.get("name"),
            "email": resume_data.get("email"),
            "phone": resume_data.get("phone"),
            "skills": resume_data.get("skills", []),
            "job_titles": resume_data.get("job_titles", []),
            "primary_query": resume_data.get("primary_query"),
        },
        "jobs": jobs,
        "total_jobs": len(jobs),
        "search_query": resume_data["primary_query"],
        "search_location": location,
    }


@app.get("/api/search-jobs")
def search_jobs_endpoint(
    keywords: str = Query(..., description="Job title or skills"),
    location: str = Query(default="", description="City, state, or country"),
    max_results: int = Query(default=20, ge=1, le=50),
    fetch_descriptions: bool = Query(default=False),
):
    """Search LinkedIn jobs directly by keyword and location."""
    try:
        jobs = search_jobs(
            keywords=keywords,
            location=location,
            max_results=max_results,
            fetch_descriptions=fetch_descriptions,
        )
    except Exception:
        logger.exception("LinkedIn search failed")
        raise HTTPException(status_code=500, detail="Failed to search jobs.")

    return {
        "jobs": jobs,
        "total_jobs": len(jobs),
        "search_query": keywords,
        "search_location": location,
    }


# ── Serve React build (production) ──────────────────────────────────────────

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
