"""
Resume parser module — extracts text and key information from PDF/DOCX files.
Supports all domains: finance, banking, insurance, accounting, marketing, HR,
sales, operations, healthcare, technology, and more.

Uses Claude AI (via Anthropic API) for intelligent resume analysis when
ANTHROPIC_API_KEY is set. Falls back to keyword-based analysis otherwise.
"""

import io
import os
import re
import json
import logging
from typing import Optional
import pdfplumber
from docx import Document

logger = logging.getLogger(__name__)


# ── Domain keyword sets ───────────────────────────────────────────────────────
# Each domain has "terms" (words that indicate this domain in the resume text)
# and "roles" (job titles to search when this domain is detected).

DOMAIN_KEYWORDS = {
    "finance_banking": {
        "terms": [
            "banking", "bank", "finance", "financial services", "investment",
            "credit", "loan", "mortgage", "treasury", "wealth management",
            "capital markets", "mutual fund", "portfolio", "fixed income",
            "equity", "nbfc", "fintech", "microfinance", "commercial bank",
            "retail banking", "corporate banking", "trade finance", "forex",
            "derivatives", "financial modeling", "valuation", "due diligence",
            "kyc", "aml", "asset management", "hedge fund", "private equity",
            "stock market", "securities", "brokerage", "demat",
        ],
        "roles": [
            "financial analyst", "credit analyst", "relationship manager",
            "investment analyst", "treasury analyst", "banking executive",
            "wealth manager", "portfolio manager", "finance executive",
        ],
    },
    "insurance": {
        "terms": [
            "insurance", "underwriting", "claims", "actuarial", "reinsurance",
            "life insurance", "general insurance", "health insurance", "premium",
            "policy", "lic", "irda", "risk assessment", "motor insurance",
            "liability insurance", "insurer", "broker", "indemnity",
        ],
        "roles": [
            "insurance executive", "insurance analyst", "underwriter",
            "claims manager", "actuarial analyst", "insurance manager",
            "insurance advisor",
        ],
    },
    "accounting": {
        "terms": [
            "accounting", "accountant", "audit", "auditing", "taxation", "gst",
            "tds", "income tax", "bookkeeping", "financial reporting", "ifrs",
            "gaap", "balance sheet", "tally", "erp sap", "chartered accountant",
            "ca ", "cma", "cpa", "payroll", "accounts payable", "accounts receivable",
            "statutory audit", "internal audit", "tax planning", "p&l", "cash flow",
        ],
        "roles": [
            "accountant", "accounts executive", "audit executive",
            "tax consultant", "finance manager", "financial controller",
        ],
    },
    "marketing": {
        "terms": [
            "marketing", "digital marketing", "brand", "seo", "sem",
            "social media", "advertising", "content marketing", "market research",
            "campaigns", "google ads", "facebook ads", "email marketing",
            "public relations", "pr", "brand awareness", "lead generation",
            "performance marketing", "influencer", "analytics",
        ],
        "roles": [
            "marketing executive", "digital marketing manager", "brand manager",
            "marketing analyst", "content manager", "seo specialist",
        ],
    },
    "hr": {
        "terms": [
            "human resources", "hr", "recruitment", "talent acquisition", "payroll",
            "training", "learning and development", "hrbp", "employee relations",
            "onboarding", "performance management", "compensation", "benefits",
            "workforce", "organisational development", "succession planning",
        ],
        "roles": [
            "hr executive", "hr manager", "recruiter",
            "talent acquisition manager", "hr business partner",
        ],
    },
    "sales": {
        "terms": [
            "sales", "business development", "b2b", "b2c", "lead generation",
            "client acquisition", "pipeline", "revenue target", "account management",
            "crm", "field sales", "retail sales", "channel sales", "key account",
            "upselling", "cross selling",
        ],
        "roles": [
            "sales executive", "business development executive",
            "account manager", "sales manager", "key account manager",
        ],
    },
    "operations": {
        "terms": [
            "operations", "supply chain", "logistics", "procurement", "inventory",
            "warehouse", "vendor management", "sourcing", "production", "quality",
            "lean", "six sigma", "process improvement", "erp", "dispatch",
        ],
        "roles": [
            "operations executive", "supply chain analyst", "logistics coordinator",
            "procurement executive", "operations manager",
        ],
    },
    "healthcare": {
        "terms": [
            "healthcare", "medical", "clinical", "hospital", "patient care",
            "nursing", "pharmacy", "pharmaceutical", "diagnostic", "mbbs",
            "bpharm", "mpharm", "lab", "radiology", "health management",
        ],
        "roles": [
            "healthcare executive", "medical representative", "clinical coordinator",
            "hospital administrator",
        ],
    },
    "education_teaching": {
        "terms": [
            "teaching", "teacher", "education", "curriculum", "school", "college",
            "lecturer", "professor", "academic", "e-learning", "edtech", "coaching",
            "faculty", "pedagogy", "classroom",
        ],
        "roles": [
            "teacher", "lecturer", "academic coordinator", "education manager",
            "curriculum developer",
        ],
    },
    "technology": {
        "terms": [
            "software", "programming", "developer", "coding", "web development",
            "full stack", "backend", "frontend", "devops", "cloud computing",
            "machine learning", "data science", "artificial intelligence", "api",
            "database", "microservices", "agile", "scrum",
        ],
        "roles": [
            "software engineer", "web developer", "data scientist",
            "devops engineer", "full stack developer",
        ],
    },
}

# ── Education pattern → domain hint ──────────────────────────────────────────
EDUCATION_PATTERNS = [
    (r'\bbanking\s+and\s+insurance\b',        "finance_banking", "insurance"),
    (r'\bfinance\s+and\s+(accounting|banking)\b', "finance_banking", "accounting"),
    (r'\baccounting\s+and\s+finance\b',        "accounting",      "finance_banking"),
    (r'\bfinancial\s+management\b',            "finance_banking",  None),
    (r'\bmarketing\s+management\b',            "marketing",        None),
    (r'\bhuman\s+resource',                    "hr",               None),
    (r'\b(b\.?com|bcom|m\.?com|mcom)\b',       "accounting",       "finance_banking"),
    (r'\b(b\.?b\.?a|bba)\b',                   "finance_banking",  "marketing"),
    (r'\b(m\.?b\.?a|mba)\b',                   "finance_banking",  "marketing"),
    (r'\b(b\.?tech|btech|b\.e\.?|be)\b',       "technology",       None),
    (r'\b(m\.?tech|mtech)\b',                  "technology",       None),
    (r'\bca\b|\bchartered\s+accountant\b',      "accounting",       None),
    (r'\bcfa\b|\bchartered\s+financial\b',      "finance_banking",  None),
    (r'\bcma\b',                                "accounting",       None),
    (r'\bllb\b|\bll\.b\b',                      None,               None),  # law - no specific domain boost
    (r'\b(b\.?sc|bsc)\s+(nursing|health)',      "healthcare",       None),
    (r'\b(b\.?sc|bsc)\b',                       None,               None),
]

# ── Non-tech job title patterns ───────────────────────────────────────────────
NON_TECH_JOB_TITLE_PATTERNS = [
    # Finance / Banking
    r'\b(financial|credit|risk|investment|portfolio|wealth|treasury|equity|'
    r'insurance|banking|mortgage|loan)\s+(analyst|manager|advisor|consultant|'
    r'officer|specialist|executive|associate)\b',
    r'\b(relationship|branch|loan|treasury|credit|operations)\s+(manager|officer|executive|head)\b',
    r'\b(chartered\s+accountant|ca|cfa|cma|acca)\b',
    r'\b(underwriter|actuari\w+|claims\s+\w+)\b',
    r'\b(bank(ing)?|insurance|nbfc|fintech)\s+(executive|officer|manager|analyst|associate)\b',
    # Accounting
    r'\b(accounts?|accounting|audit|tax|finance)\s+(manager|executive|officer|analyst|consultant|head|controller)\b',
    r'\b(senior|junior|assistant)?\s*(accountant|auditor|bookkeeper)\b',
    # Marketing / Sales
    r'\b(marketing|digital\s+marketing|brand|content|seo|growth|performance)\s+'
    r'(manager|executive|specialist|analyst|lead|head|strategist)\b',
    r'\b(sales|business\s+development|account|key\s+account)\s+'
    r'(manager|executive|representative|associate|officer|head)\b',
    # HR
    r'\b(human\s+resources?|hr|talent|recruitment|people)\s+'
    r'(manager|executive|specialist|partner|coordinator|head|generalist)\b',
    # Operations
    r'\b(operations?|supply\s+chain|logistics?|procurement|warehouse)\s+'
    r'(manager|executive|analyst|coordinator|head|officer)\b',
    # General leadership
    r'\b(general|deputy|assistant|associate)\s+manager\b',
    r'\b(vice\s+president|vp|avp|svp)\s+\w+\b',
    r'\bhead\s+of\s+[\w\s]+\b',
    r'\b(chief\s+\w+\s+officer|c[a-z]o)\b',
]

# ── Tech skills (legacy — kept for technology-domain resumes) ─────────────────
TECH_SKILLS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "bash",
    "react", "angular", "vue", "next.js", "html", "css", "tailwind",
    "node.js", "fastapi", "django", "flask", "spring",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform",
    "machine learning", "deep learning", "tensorflow", "pytorch",
    "git", "agile", "scrum", "rest api", "microservices", "kafka",
}


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


# ── Field extractors ──────────────────────────────────────────────────────────

def extract_email(text: str) -> Optional[str]:
    match = re.search(r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}', text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    match = re.search(
        r'(\+?\d{1,3}[\s.-]?)?(\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}', text
    )
    return match.group(0).strip() if match else None


def extract_name(text: str) -> Optional[str]:
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line.split()) <= 5 and re.match(r'^[A-Za-z\s\-\.]+$', line):
            return line
    return None


def extract_tech_skills(text: str) -> list[str]:
    lower_text = text.lower()
    found = set()
    for skill in TECH_SKILLS:
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, lower_text):
            found.add(skill)
    return sorted(found)


def extract_all_skills(text: str, domain: str) -> list[str]:
    """Extract skills relevant to the detected domain plus any tech skills."""
    lower_text = text.lower()
    found = set()

    # Get domain-specific skills from DOMAIN_KEYWORDS terms
    domain_terms = DOMAIN_KEYWORDS.get(domain, {}).get("terms", [])
    for term in domain_terms:
        if term.strip() and re.search(r'\b' + re.escape(term.strip()) + r'\b', lower_text):
            found.add(term.strip())

    # Always check tech skills too (useful for hybrid profiles)
    for skill in TECH_SKILLS:
        if re.search(r'\b' + re.escape(skill) + r'\b', lower_text):
            found.add(skill)

    # Non-tech skill phrases common in business resumes
    business_skills = [
        "ms excel", "microsoft excel", "ms office", "powerpoint", "ms word",
        "financial modeling", "financial analysis", "data analysis",
        "project management", "team management", "leadership",
        "communication", "problem solving", "customer service",
        "relationship management", "negotiation", "presentation",
        "tally", "sap", "quickbooks", "zoho", "salesforce", "hubspot",
        "bloomberg", "reuters", "capital iq",
    ]
    for skill in business_skills:
        if skill in lower_text:
            found.add(skill)

    return sorted(found)


def extract_job_titles(text: str) -> list[str]:
    """Extract job titles from both tech and non-tech patterns."""
    lower_text = text.lower()
    found = set()

    all_patterns = NON_TECH_JOB_TITLE_PATTERNS + [
        r'\b(senior|junior|lead|principal|staff|associate)?\s*'
        r'(software|frontend|backend|fullstack|data|ml|ai|devops|cloud|platform)\s*'
        r'(engineer|developer|architect|scientist|analyst|specialist)\b',
        r'\b(data scientist|data engineer|data analyst|business analyst)\b',
        r'\bdevops\s*(engineer|specialist)?\b',
    ]
    for pattern in all_patterns:
        try:
            matches = re.findall(pattern, lower_text, re.IGNORECASE)
            for match in matches:
                title = " ".join(p for p in (match if isinstance(match, tuple) else [match]) if p).strip()
                if title and len(title) > 3:
                    found.add(title.title())
        except re.error:
            continue

    return sorted(found)


def extract_education(text: str) -> list[str]:
    """Return matched education fields/degrees from the resume."""
    lower_text = text.lower()
    results = []
    for pattern, *_ in EDUCATION_PATTERNS:
        matches = re.findall(pattern, lower_text, re.IGNORECASE)
        for m in matches:
            val = (m if isinstance(m, str) else " ".join(m)).strip()
            if val and val not in results:
                results.append(val)
    return results


# ── Domain detection ──────────────────────────────────────────────────────────

def detect_domain(text: str) -> str:
    """
    Score each domain by counting how many of its keywords appear in the text.
    Returns the best-matching domain name.
    """
    lower_text = text.lower()
    scores: dict[str, int] = {}

    for domain, data in DOMAIN_KEYWORDS.items():
        score = 0
        for term in data["terms"]:
            t = term.strip()
            if not t:
                continue
            count = len(re.findall(r'\b' + re.escape(t) + r'\b', lower_text))
            score += count
        scores[domain] = score

    # Boost domains that appear in education patterns
    for pattern, primary, secondary in EDUCATION_PATTERNS:
        if re.search(pattern, lower_text, re.IGNORECASE):
            if primary and primary in scores:
                scores[primary] = scores[primary] + 8
            if secondary and secondary in scores:
                scores[secondary] = scores[secondary] + 4

    best = max(scores, key=lambda k: scores[k])
    # If no domain is clearly detected, fall back to technology (old behaviour)
    if scores[best] == 0:
        return "technology"
    return best


# ── Multi-query builder ───────────────────────────────────────────────────────

def build_search_queries(
    domain: str,
    job_titles: list[str],
    education: list[str],
    text: str,
) -> list[str]:
    """
    Build 2–3 targeted LinkedIn search queries for the resume.
    Uses detected job titles first, then domain-specific fallbacks.
    """
    queries: list[str] = []

    # Use extracted job titles (clean them up)
    for title in job_titles[:2]:
        clean = title.strip().lower()
        # Skip very generic or very long titles
        if clean and len(clean.split()) <= 5 and clean not in queries:
            queries.append(clean)

    # Education-specific overrides
    lower_text = text.lower()
    if re.search(r'\bbanking\s+and\s+insurance\b', lower_text):
        for q in ["banking executive", "insurance executive", "financial services executive"]:
            if q not in queries:
                queries.insert(0, q)
                break

    # Domain fallback roles
    domain_roles = DOMAIN_KEYWORDS.get(domain, {}).get("roles", [])
    for role in domain_roles:
        if len(queries) >= 3:
            break
        if role not in queries:
            queries.append(role)

    # Combined domain queries for dual-domain resumes
    if domain in ("finance_banking", "insurance"):
        combo = "financial services executive"
        if len(queries) < 3 and combo not in queries:
            queries.append(combo)

    # Absolute fallback
    if not queries:
        queries.append("professional")

    return queries[:3]


# ── Relevance scoring ─────────────────────────────────────────────────────────

def get_domain_filter_words(domain: str) -> tuple[list[str], list[str]]:
    """
    Returns (positive_words, negative_words) for post-search relevance filtering.
    positive_words: words that indicate a job IS relevant for this domain
    negative_words: words that indicate a job is clearly NOT for this domain
    """
    positive = [t.strip() for t in DOMAIN_KEYWORDS.get(domain, {}).get("terms", []) if t.strip()]
    positive += [r.split()[0] for r in DOMAIN_KEYWORDS.get(domain, {}).get("roles", [])]

    # What's clearly NOT relevant for non-tech resumes
    tech_negative = [
        "software engineer", "software developer", "frontend developer",
        "backend developer", "full stack developer", "web developer",
        "devops engineer", "python developer", "java developer",
        "react developer", "android developer", "ios developer",
        "machine learning engineer", "data engineer", "cloud engineer",
    ]

    # What's clearly NOT relevant for tech resumes
    non_tech_negative = [
        "insurance agent", "loan officer", "bank teller",
    ]

    if domain == "technology":
        return positive, non_tech_negative
    else:
        return positive, tech_negative


# ── Claude AI resume analysis ─────────────────────────────────────────────────

def _analyze_with_claude(text: str) -> Optional[dict]:
    """
    Use Claude AI to deeply understand the resume and generate targeted job
    search queries. Returns structured dict or None if API is unavailable.

    Requires ANTHROPIC_API_KEY environment variable to be set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""You are an expert career consultant. Analyze this resume carefully and extract key information to find the most relevant job listings on LinkedIn.

Resume:
\"\"\"
{text[:4000]}
\"\"\"

Return ONLY a valid JSON object (no markdown, no explanation) with these fields:
{{
  "domain": "primary industry — one of: finance_banking, insurance, accounting, marketing, hr, sales, operations, healthcare, technology, education, legal, other",
  "subdomain": "specific area e.g. retail banking, life insurance, digital marketing, talent acquisition",
  "experience_level": "one of: fresher, entry, mid_senior, senior, executive",
  "job_titles": ["list of 3-5 job titles this person is qualified for or seeking"],
  "skills": ["list of 10-15 most relevant skills from the resume"],
  "education": ["qualifications/degrees e.g. BCom Banking and Insurance, MBA Finance"],
  "search_queries": [
    "query1 — 2-5 words, most relevant role for this person on LinkedIn",
    "query2 — alternative relevant role or specialisation",
    "query3 — broader related role to cast a wider net"
  ]
}}

Rules for search_queries:
- Match the person's ACTUAL domain and level (not tech if they are in finance)
- A BCom/MBA in Banking & Insurance → queries like 'banking executive', 'insurance analyst', 'financial services trainee'
- A fresher/recent graduate → include 'trainee', 'associate', 'junior', or 'entry level' terms
- Queries must be specific enough to return relevant jobs, not generic like 'manager' or 'executive' alone
- Include both internship-friendly and full-time variations if experience_level is fresher/entry"""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
            timeout=20,
        )

        raw = message.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        result = json.loads(raw)
        logger.info("Claude analysis: domain=%s level=%s queries=%s",
                    result.get("domain"), result.get("experience_level"), result.get("search_queries"))
        return result

    except Exception as exc:
        logger.warning("Claude analysis failed (%s), falling back to keyword analysis.", exc)
        return None


# ── Main entry point ──────────────────────────────────────────────────────────

def parse_resume(file_bytes: bytes, filename: str) -> dict:
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith((".docx", ".doc")):
        text = extract_text_from_docx(file_bytes)
    elif filename_lower.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {filename}")

    # Always run keyword-based extraction (used as fallback and to fill gaps)
    domain_kw         = detect_domain(text)
    education_kw      = extract_education(text)
    job_titles_kw     = extract_job_titles(text)
    skills_kw         = extract_all_skills(text, domain_kw)
    search_queries_kw = build_search_queries(domain_kw, job_titles_kw, education_kw, text)

    # Try Claude AI for smarter analysis
    ai = _analyze_with_claude(text)

    # Merge: prefer AI results, fill missing fields with keyword results
    domain      = ai.get("domain") or domain_kw          if ai else domain_kw
    education   = ai.get("education") or education_kw    if ai else education_kw
    job_titles  = ai.get("job_titles") or job_titles_kw  if ai else job_titles_kw
    skills      = ai.get("skills") or skills_kw          if ai else skills_kw
    exp_level   = ai.get("experience_level", "")         if ai else ""

    search_queries = (
        [q for q in (ai.get("search_queries") or []) if q]
        or search_queries_kw
    )
    if not search_queries:
        search_queries = search_queries_kw

    # Add experience-level terms to queries for freshers/interns
    if exp_level in ("fresher", "entry") and search_queries:
        levelled = []
        for q in search_queries:
            low = q.lower()
            if not any(w in low for w in ("intern", "trainee", "fresher", "entry", "junior", "associate", "graduate")):
                levelled.append(q + " trainee")
            levelled.append(q)
        search_queries = list(dict.fromkeys(levelled))[:4]  # deduplicate, keep order

    positive_words, negative_words = get_domain_filter_words(domain)
    primary_query = search_queries[0] if search_queries else "professional"

    return {
        "name":           extract_name(text),
        "email":          extract_email(text),
        "phone":          extract_phone(text),
        "skills":         skills,
        "job_titles":     job_titles,
        "education":      education,
        "domain":         domain,
        "experience_level": exp_level,
        "primary_query":  primary_query,
        "search_queries": search_queries,
        "positive_words": positive_words,
        "negative_words": negative_words,
        "ai_powered":     ai is not None,
        "raw_text_preview": text[:500],
    }
