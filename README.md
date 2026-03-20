# LinkedIn Job Finder

Upload your resume and instantly find matching LinkedIn job listings.
Optionally sign in with LinkedIn to enrich your profile and get better matches.

**Live demo**: Deploy to Vercel in one click (see below).

---

## Features

- **Resume upload** — PDF, DOCX, DOC, TXT (up to 5 MB)
- **Automatic skill & role extraction** — detects 80+ technical skills and job titles
- **LinkedIn job scraping** — searches LinkedIn's public jobs guest API
- **LinkedIn OAuth sign-in** — optional; enriches name/email from your profile
- **Rich filters** (all optional):
  - Work setting: Remote, Hybrid, On-site
  - Job type: Full-time, Part-time, Contract, Internship, Temporary, Volunteer
  - Experience level: Internship → Executive
  - Date posted: Any time / Past month / Past week / Past 24 hours
  - Sort: Most relevant / Most recent
  - Easy Apply only

---

## Deploy to Vercel

### 1. Push this repo to GitHub

```bash
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

### 2. Import in Vercel

Go to https://vercel.com/new → Import the repository.

Vercel will auto-detect `vercel.json` and:
- Build the React frontend with Vite (`frontend/dist`)
- Deploy the FastAPI backend as a Python serverless function (`api/index.py`)

### 3. Add Environment Variables in Vercel

In your Vercel project → **Settings → Environment Variables**, add:

| Variable | Value |
|---|---|
| `LINKEDIN_CLIENT_ID` | From your LinkedIn app |
| `LINKEDIN_CLIENT_SECRET` | From your LinkedIn app |
| `LINKEDIN_REDIRECT_URI` | `https://<project>.vercel.app/api/auth/linkedin/callback` |
| `FRONTEND_URL` | `https://<project>.vercel.app` |

### 4. LinkedIn App Setup

1. Go to https://www.linkedin.com/developers/apps/new
2. Add redirect URI: `https://<project>.vercel.app/api/auth/linkedin/callback`
3. Enable scopes: `openid`, `profile`, `email`

---

## Local Development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env    # fill in your credentials
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev        # http://localhost:5173
```

---

## Project Structure

```
Jobs/
├── api/
│   └── index.py              # Vercel serverless entry (imports FastAPI app)
├── backend/
│   ├── main.py               # FastAPI app + all endpoints
│   ├── resume_parser.py      # PDF/DOCX/TXT parsing + skill extraction
│   ├── linkedin_scraper.py   # LinkedIn public jobs scraper + filters
│   ├── linkedin_auth.py      # LinkedIn OAuth 2.0 flow
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   │       ├── JobFilters.jsx     # All search filters UI
│   │       ├── ResumeUpload.jsx
│   │       ├── LinkedInSignIn.jsx
│   │       ├── JobResults.jsx
│   │       └── JobCard.jsx
│   └── package.json
├── vercel.json               # Vercel deployment config
├── requirements.txt          # Root-level (used by Vercel Python runtime)
└── .env.example
```

---

## Notes

- LinkedIn may occasionally rate-limit the scraper (HTTP 429). If results are empty, retry after a moment.
- LinkedIn OAuth (`Sign in with LinkedIn`) enhances the profile display but is optional — the app works without it.
- This project is not affiliated with LinkedIn.
