"""
FastAPI backend for LinkedIn Job Finder.
"""

import logging
import os
from typing import Optional, List

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
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


def _score_and_filter_jobs(
    jobs: list[dict],
    positive_words: list[str],
    negative_words: list[str],
) -> list[dict]:
    """
    Score each job by how well its title matches the resume's domain.
    Jobs with clearly irrelevant titles (negative matches) are pushed to the end.
    Jobs with relevant titles (positive matches) are surfaced first.
    """
    def score(job: dict) -> int:
        title = (job.get("title") or "").lower()
        s = 0
        for word in positive_words:
            if word.lower() in title:
                s += 2
        for phrase in negative_words:
            if phrase.lower() in title:
                s -= 5
        return s

    scored = [(score(j), j) for j in jobs]
    # Remove jobs with a very negative score (clearly wrong domain)
    scored = [(s, j) for s, j in scored if s > -4]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [j for _, j in scored]


def _build_filter_kwargs(
    job_types: Optional[List[str]],
    experience_levels: Optional[List[str]],
    work_types: Optional[List[str]],
    date_posted: Optional[str],
    easy_apply: bool,
    sort_by: str,
) -> dict:
    return {
        "job_types": job_types or [],
        "experience_levels": experience_levels or [],
        "work_types": work_types or [],
        "date_posted": date_posted,
        "easy_apply": easy_apply,
        "sort_by": sort_by,
    }


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── LinkedIn OAuth ────────────────────────────────────────────────────────────

@app.get("/api/auth/linkedin/login")
def linkedin_login():
    auth_url, _ = generate_login_url()
    return RedirectResponse(url=auth_url)


@app.get("/api/auth/linkedin/callback")
async def linkedin_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    error_description: Optional[str] = Query(default=None),
):
    if error:
        return RedirectResponse(
            url=f"{FRONTEND_URL}?auth_error={error}&error_description={error_description or ''}"
        )
    if not code or not state:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=missing_params")

    try:
        auth_data = await get_linkedin_profile_and_token(code, state)
    except HTTPException as exc:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error={exc.detail}")

    from urllib.parse import urlencode
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
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    token = authorization.split(" ", 1)[1]
    return await fetch_linkedin_profile(token)


# ── Resume upload ─────────────────────────────────────────────────────────────

@app.post("/api/parse-resume")
async def parse_resume_endpoint(
    file: UploadFile = File(...),
    location: Optional[str] = Query(default=""),
    max_results: int = Query(default=20, ge=1, le=50),
    fetch_descriptions: bool = Query(default=False),
    linkedin_name: Optional[str] = Query(default=None),
    # ── filters ──────────────────────────────────────────────────────────
    job_types: Optional[List[str]] = Query(default=None),
    experience_levels: Optional[List[str]] = Query(default=None),
    work_types: Optional[List[str]] = Query(default=None),
    date_posted: Optional[str] = Query(default=None),
    easy_apply: bool = Query(default=False),
    sort_by: str = Query(default="relevant"),
):
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Upload a PDF, DOCX, or TXT file.",
        )

    file_bytes = await file.read()
    if len(file_bytes) / (1024 * 1024) > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"File too large. Max {MAX_FILE_SIZE_MB} MB.")

    try:
        resume_data = parse_resume(file_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Resume parsing failed")
        raise HTTPException(status_code=500, detail="Failed to parse resume.")

    if linkedin_name and not resume_data.get("name"):
        resume_data["name"] = linkedin_name

    search_queries = resume_data.get("search_queries") or [resume_data["primary_query"]]
    positive_words = resume_data.get("positive_words", [])
    negative_words = resume_data.get("negative_words", [])

    # Search with all queries and combine, deduplicating by job id
    all_jobs: list[dict] = []
    seen_ids: set[str] = set()
    per_query = max(15, max_results)
    filter_kwargs = _build_filter_kwargs(job_types, experience_levels, work_types, date_posted, easy_apply, sort_by)

    for query in search_queries:
        try:
            results = search_jobs(
                keywords=query,
                location=location,
                max_results=per_query,
                fetch_descriptions=fetch_descriptions,
                **filter_kwargs,
            )
            for job in results:
                jid = job.get("id") or job.get("url") or ""
                if jid not in seen_ids:
                    seen_ids.add(jid)
                    all_jobs.append(job)
        except Exception:
            logger.exception("LinkedIn search failed for query: %s", query)

    # Score and filter jobs for relevance
    all_jobs = _score_and_filter_jobs(all_jobs, positive_words, negative_words)
    all_jobs = all_jobs[:max_results]

    return {
        "resume": {
            "name": resume_data.get("name"),
            "email": resume_data.get("email"),
            "phone": resume_data.get("phone"),
            "skills": resume_data.get("skills", []),
            "job_titles": resume_data.get("job_titles", []),
            "education": resume_data.get("education", []),
            "domain": resume_data.get("domain", ""),
            "primary_query": resume_data.get("primary_query"),
            "search_queries": search_queries,
        },
        "jobs": all_jobs,
        "total_jobs": len(all_jobs),
        "search_query": " · ".join(search_queries),
        "search_location": location,
    }


# ── Direct job search ─────────────────────────────────────────────────────────

@app.get("/api/search-jobs")
def search_jobs_endpoint(
    keywords: str = Query(...),
    location: str = Query(default=""),
    max_results: int = Query(default=20, ge=1, le=50),
    fetch_descriptions: bool = Query(default=False),
    # ── filters ──────────────────────────────────────────────────────────
    job_types: Optional[List[str]] = Query(default=None),
    experience_levels: Optional[List[str]] = Query(default=None),
    work_types: Optional[List[str]] = Query(default=None),
    date_posted: Optional[str] = Query(default=None),
    easy_apply: bool = Query(default=False),
    sort_by: str = Query(default="relevant"),
):
    try:
        jobs = search_jobs(
            keywords=keywords,
            location=location,
            max_results=max_results,
            fetch_descriptions=fetch_descriptions,
            **_build_filter_kwargs(job_types, experience_levels, work_types, date_posted, easy_apply, sort_by),
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


# ── Serve React build (local production) ─────────────────────────────────────

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
