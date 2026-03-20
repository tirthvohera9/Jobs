"""
LinkedIn job scraper using the public (no-auth) LinkedIn Jobs guest API.

LinkedIn exposes a public jobs listing endpoint used by their jobs search page:
  https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
This endpoint returns HTML fragments that can be parsed with BeautifulSoup.
"""

import re
import time
import random
import logging
from typing import Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"

# Rotate through a few realistic User-Agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def _get_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.linkedin.com/jobs/search/",
        "Cache-Control": "no-cache",
    }


def _fetch(url: str, params: dict, retries: int = 3) -> Optional[str]:
    """HTTP GET with simple retry logic."""
    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                params=params,
                headers=_get_headers(),
                timeout=15,
            )
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
    """Parse the HTML fragment returned by LinkedIn's guest jobs API."""
    soup = BeautifulSoup(html, "lxml")
    jobs = []

    for card in soup.find_all("li"):
        try:
            # Job ID
            entity = card.find("div", {"data-entity-urn": True})
            if not entity:
                continue
            urn = entity.get("data-entity-urn", "")
            job_id_match = re.search(r'\d+', urn)
            job_id = job_id_match.group(0) if job_id_match else None

            # Title
            title_tag = card.find("h3", class_=re.compile("base-search-card__title"))
            title = title_tag.get_text(strip=True) if title_tag else "N/A"

            # Company
            company_tag = card.find("h4", class_=re.compile("base-search-card__subtitle"))
            company = company_tag.get_text(strip=True) if company_tag else "N/A"

            # Location
            location_tag = card.find("span", class_=re.compile("job-search-card__location"))
            location = location_tag.get_text(strip=True) if location_tag else "N/A"

            # Posted date
            date_tag = card.find("time")
            posted_date = date_tag.get("datetime", "") if date_tag else ""

            # Job URL
            link_tag = card.find("a", class_=re.compile("base-card__full-link"))
            if not link_tag:
                link_tag = card.find("a", href=re.compile(r"/jobs/view/"))
            job_url = link_tag.get("href", "").split("?")[0] if link_tag else ""

            # Company logo
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
                "description": None,  # filled in optionally
            })
        except Exception as exc:
            logger.debug("Error parsing card: %s", exc)
            continue

    return jobs


def _fetch_job_description(job_id: str) -> Optional[str]:
    """Fetch the description for a single job posting (best-effort)."""
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
) -> list[dict]:
    """
    Search LinkedIn jobs using the public guest API.

    Args:
        keywords: Job title / skill keywords (e.g. "python developer")
        location: City, state, or country filter (e.g. "United States")
        max_results: Maximum number of jobs to return (max ~50 per call)
        fetch_descriptions: Whether to fetch full job descriptions (slower)

    Returns:
        List of job dicts.
    """
    params = {
        "keywords": keywords,
        "location": location,
        "trk": "public_jobs_jobs-search-bar_search-submit",
        "position": 1,
        "pageNum": 0,
        "start": 0,
        "count": min(max_results, 25),
    }

    html = _fetch(SEARCH_URL, params)
    if not html:
        return []

    jobs = _parse_job_cards(html)

    # Fetch a second page if needed
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
