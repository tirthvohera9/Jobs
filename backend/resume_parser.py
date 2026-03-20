"""
Resume parser module — extracts text and key information from PDF/DOCX files.
"""

import io
import re
from typing import Optional
import pdfplumber
from docx import Document


# Common technical skills list for keyword extraction
TECH_SKILLS = {
    # Languages
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "bash",
    "shell", "perl", "haskell", "elixir", "clojure",
    # Frontend
    "react", "angular", "vue", "next.js", "nuxt", "svelte", "html", "css",
    "sass", "less", "tailwind", "bootstrap", "jquery", "redux", "webpack",
    "vite", "graphql",
    # Backend
    "node.js", "express", "fastapi", "django", "flask", "spring", "laravel",
    "rails", "asp.net", "nestjs", "gin", "fiber",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
    "cassandra", "dynamodb", "firebase", "supabase", "oracle",
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github actions", "ci/cd", "linux", "nginx", "apache",
    # Data & AI
    "machine learning", "deep learning", "tensorflow", "pytorch", "pandas",
    "numpy", "scikit-learn", "keras", "spark", "hadoop", "airflow", "dbt",
    "tableau", "power bi", "nlp", "computer vision", "llm",
    # Other
    "git", "agile", "scrum", "rest api", "microservices", "kafka", "rabbitmq",
    "websocket", "oauth", "jwt", "graphql",
}

# Common job title keywords
JOB_TITLE_PATTERNS = [
    r'\b(senior|junior|lead|principal|staff|associate)?\s*'
    r'(software|frontend|backend|fullstack|full[\s-]stack|mobile|ios|android|'
    r'web|data|ml|ai|machine learning|devops|cloud|platform|site reliability|'
    r'qa|quality assurance|security|embedded|systems)\s*'
    r'(engineer|developer|architect|scientist|analyst|specialist|manager|'
    r'consultant|intern)\b',
    r'\b(product|project|program|engineering|technical|technology)\s*manager\b',
    r'\b(ui|ux|ui/ux)\s*(designer|developer|engineer)?\b',
    r'\b(data scientist|data engineer|data analyst|business analyst)\b',
    r'\bdevops\s*(engineer|specialist|architect)?\b',
    r'\b(cto|ceo|cio|vp\s+of\s+engineering)\b',
]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract raw text from a PDF file."""
    text_parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract raw text from a DOCX file."""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def extract_email(text: str) -> Optional[str]:
    match = re.search(r'[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}', text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    match = re.search(
        r'(\+?\d{1,3}[\s.-]?)?(\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}', text
    )
    return match.group(0).strip() if match else None


def extract_skills(text: str) -> list[str]:
    """Extract technical skills from resume text."""
    lower_text = text.lower()
    found = set()
    for skill in TECH_SKILLS:
        # Use word boundary matching for short skills to avoid false positives
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, lower_text):
            found.add(skill)
    return sorted(found)


def extract_job_titles(text: str) -> list[str]:
    """Extract likely job titles / target roles from resume text."""
    lower_text = text.lower()
    found = set()
    for pattern in JOB_TITLE_PATTERNS:
        matches = re.findall(pattern, lower_text, re.IGNORECASE)
        for match in matches:
            title = " ".join(part for part in match if part).strip()
            if title:
                found.add(title.title())
    return sorted(found)


def extract_name(text: str) -> Optional[str]:
    """Heuristic: first non-empty line is usually the candidate's name."""
    for line in text.split("\n"):
        line = line.strip()
        # Skip lines that look like section headers or contain only numbers/symbols
        if line and len(line.split()) <= 5 and re.match(r'^[A-Za-z\s\-\.]+$', line):
            return line
    return None


def parse_resume(file_bytes: bytes, filename: str) -> dict:
    """
    Main entry point. Returns structured info extracted from the resume.
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith((".docx", ".doc")):
        text = extract_text_from_docx(file_bytes)
    elif filename_lower.endswith(".txt"):
        text = file_bytes.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {filename}")

    skills = extract_skills(text)
    job_titles = extract_job_titles(text)

    # Build a search query: prefer job titles; fall back to top skills
    if job_titles:
        primary_query = job_titles[0]
    elif skills:
        primary_query = " ".join(skills[:3])
    else:
        primary_query = "software engineer"

    return {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "skills": skills,
        "job_titles": job_titles,
        "primary_query": primary_query,
        "raw_text_preview": text[:500],
    }
