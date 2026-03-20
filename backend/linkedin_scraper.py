"""
LinkedIn job scraper using the public (no-auth) LinkedIn Jobs guest API.

LinkedIn exposes a public jobs listing endpoint used by their jobs search page:
  https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
This endpoint returns HTML fragments that can be parsed with BeautifulSoup.

Supported LinkedIn filter codes
---------------------------------
f_JT  (job type)        F=Full-time  P=Part-time  C=Contract  T=Temporary
                        V=Volunteer  I=Internship
f_E   (exp level)       1=Internship 2=Entry 3=Associate 4=Mid-Senior
                        5=Director   6=Executive
f_TPR (date posted)     r86400=24h   r604800=1wk  r2592000=1mo
f_WT  (work setting)    1=On-site    2=Remote     3=Hybrid
f_EA  (easy apply)      true
sortBy                  R=Relevant   DD=Most-recent
"""

import re
import time
import random
import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# ── public filter mappings ────────────────────────────────────────────────────

JOB_TYPE_MAP = {
    "full_time":  "F",
    "part_time":  "P",
    "contract":   "C",
    "temporary":  "T",
    "volunteer":  "V",
    "internship": "I",
}

EXP_LEVEL_MAP = {
    "internship": "1",
    "entry":      "2",
    "associate":  "3",
    "mid_senior": "4",
    "director":   "5",
    "executive":  "6",
}

WORK_TYPE_MAP = {
    "on_site": "1",
    "remote":  "2",
    "hybrid":  "3",
}

DATE_POSTED_MAP = {
    "day":   "r86400",
    "week":  "r604800",
    "month": "r2592000",
}

SORT_MAP = {
    "relevant":  "R",
    "recent":    "DD",
}


def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.linkedin.com/jobs/search/",
        "Cache-Control": "no-cache",
    }


def _fetch(url: str, params: dict, retries: int = 3) -> Optional[str]:
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, headers=_get_headers(), timeout=20)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 429:
                wait = 2 ** attempt + random.uniform(0, 1)
                logger.warning("Rate-limited (429). Waiting %.1fs …", wait)
                time.sleep(wait)
            else:
                logger.warning("HTTP %s for %s", resp.status_code, url)
                break
        except requests.RequestException as exc:
            logger.error("Request error: %s", exc)
            time.sleep(1)
    return None


def _parse_job_cards(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    jobs = []
    for card in soup.find_all("li"):
        try:
            entity = card.find("div", {"data-entity-urn": True})
            if not entity:
                continue
            urn = entity.get("data-entity-urn", "")
            job_id_match = re.search(r'\d+', urn)
            job_id = job_id_match.group(0) if job_id_match else None

            title_tag = card.find("h3", class_=re.compile("base-search-card__title"))
            title = title_tag.get_text(strip=True) if title_tag else "N/A"

            company_tag = card.find("h4", class_=re.compile("base-search-card__subtitle"))
            company = company_tag.get_text(strip=True) if company_tag else "N/A"

            location_tag = card.find("span", class_=re.compile("job-search-card__location"))
            location = location_tag.get_text(strip=True) if location_tag else "N/A"

            date_tag = card.find("time")
            posted_date = date_tag.get("datetime", "") if date_tag else ""

            link_tag = card.find("a", class_=re.compile("base-card__full-link"))
            if not link_tag:
                link_tag = card.find("a", href=re.compile(r"/jobs/view/"))
            job_url = link_tag.get("href", "").split("?")[0] if link_tag else ""

            img_tag = card.find("img", class_=re.compile("artdeco-entity-image"))
            logo_url = img_tag.get("data-delayed-url", "") if img_tag else ""

            if title == "N/A" and company == "N/A":
                continue

            jobs.append({
                "id": job_id,
                "title": title,
                "company": company,
                "location": location,
                "posted_date": posted_date,
                "url": job_url,
                "logo_url": logo_url,
                "description": None,
            })
        except Exception as exc:
            logger.debug("Error parsing card: %s", exc)
    return jobs


def _fetch_job_description(job_id: str) -> Optional[str]:
    html = _fetch(DETAIL_URL.format(job_id=job_id), params={})
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    desc_tag = soup.find("div", class_=re.compile("description__text"))
    if desc_tag:
        return desc_tag.get_text(separator="\n", strip=True)[:1500]
    return None


def search_jobs(
    keywords: str,
    location: str = "",
    max_results: int = 20,
    fetch_descriptions: bool = False,
    # ── filters ──────────────────────────────────────────────────────────
    job_types: Optional[list[str]] = None,       # ["full_time","internship",…]
    experience_levels: Optional[list[str]] = None, # ["entry","mid_senior",…]
    work_types: Optional[list[str]] = None,      # ["remote","hybrid","on_site"]
    date_posted: Optional[str] = None,           # "day"|"week"|"month"
    easy_apply: bool = False,
    sort_by: str = "relevant",                   # "relevant"|"recent"
) -> list[dict]:
    """
    Search LinkedIn jobs using the public guest API with optional filters.
    """
    params: dict = {
        "keywords": keywords,
        "location": location,
        "trk": "public_jobs_jobs-search-bar_search-submit",
        "position": 1,
        "pageNum": 0,
        "start": 0,
        "count": min(max_results, 25),
    }

    # Job type filter (comma-joined LinkedIn codes)
    if job_types:
        codes = [JOB_TYPE_MAP[t] for t in job_types if t in JOB_TYPE_MAP]
        if codes:
            params["f_JT"] = ",".join(codes)

    # Experience level filter
    if experience_levels:
        codes = [EXP_LEVEL_MAP[e] for e in experience_levels if e in EXP_LEVEL_MAP]
        if codes:
            params["f_E"] = ",".join(codes)

    # Work type filter
    if work_types:
        codes = [WORK_TYPE_MAP[w] for w in work_types if w in WORK_TYPE_MAP]
        if codes:
            params["f_WT"] = ",".join(codes)

    # Date posted filter
    if date_posted and date_posted in DATE_POSTED_MAP:
        params["f_TPR"] = DATE_POSTED_MAP[date_posted]

    # Easy Apply filter
    if easy_apply:
        params["f_EA"] = "true"

    # Sort order
    if sort_by in SORT_MAP:
        params["sortBy"] = SORT_MAP[sort_by]

    html = _fetch(SEARCH_URL, params)
    if not html:
        return []

    jobs = _parse_job_cards(html)

    # Fetch second page if needed
    if len(jobs) < max_results and len(jobs) >= 25:
        params["start"] = 25
        params["count"] = min(max_results - len(jobs), 25)
        time.sleep(random.uniform(0.5, 1.5))
        html2 = _fetch(SEARCH_URL, params)
        if html2:
            jobs.extend(_parse_job_cards(html2))

    jobs = jobs[:max_results]

    if fetch_descriptions:
        for job in jobs:
            if job.get("id"):
                job["description"] = _fetch_job_description(job["id"])
                time.sleep(random.uniform(0.3, 0.8))

    return jobs
