# LinkedIn Job Finder

Upload your resume and instantly find matching LinkedIn job listings.
Optionally sign in with LinkedIn to enrich your profile and get better matches.

---

## Features

- **Resume upload** — PDF, DOCX, DOC, TXT (up to 5 MB)
- **Automatic skill extraction** — detects 80+ technical skills from your resume
- **Job title detection** — identifies your target roles via pattern matching
- **LinkedIn job scraping** — searches LinkedIn's public jobs page (no API key needed)
- **LinkedIn OAuth sign-in** — optional; enriches name/email and future profile features
- **Manual keyword search** — search without uploading a resume
- **Location filter** — narrow results to a city, state, or country

---

## Quick Start (Local Development)

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App available at: http://localhost:5173

---

## LinkedIn OAuth Setup (optional but recommended)

1. Go to https://www.linkedin.com/developers/apps/new
2. Create a new app (any name/company is fine for local dev)
3. Under **Auth**, add the redirect URL:
   `http://localhost:8000/api/auth/linkedin/callback`
4. Request these OAuth scopes: `openid`, `profile`, `email`
5. Copy your **Client ID** and **Client Secret**

Create a `.env` file in the project root:

```env
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_REDIRECT_URI=http://localhost:8000/api/auth/linkedin/callback
FRONTEND_URL=http://localhost:5173
```

---

## Docker (Production)

```bash
cp .env.example .env
# Fill in your LinkedIn credentials in .env
docker-compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

---

## Project Structure

```
Jobs/
├── backend/
│   ├── main.py             # FastAPI app + all endpoints
│   ├── resume_parser.py    # PDF/DOCX/TXT parsing + skill extraction
│   ├── linkedin_scraper.py # LinkedIn public jobs scraper
│   ├── linkedin_auth.py    # LinkedIn OAuth 2.0 flow
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   │       ├── ResumeUpload.jsx
│   │       ├── LinkedInSignIn.jsx
│   │       ├── JobResults.jsx
│   │       └── JobCard.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Notes

- LinkedIn may occasionally rate-limit the public scraper (HTTP 429). If results are empty, wait a moment and retry.
- The LinkedIn Jobs API (official partner API) is not used here — the scraper targets the public jobs guest endpoint used by LinkedIn's own job search page.
- This project is not affiliated with LinkedIn.
