# M&A Prospecting Platform

AI-powered buyer discovery for sell-side M&A mandates. Paste a target company URL and the platform automatically profiles the company, generates a ranked list of potential acquirers, extracts buy-side signals, and scores every prospect — all powered by Claude.

---

## How It Works

The platform runs a 4-step pipeline:


URL → [1] Profile Target → [2] Generate Prospects → [3] Extract Signals → [4] Score & Rank


| Step | What happens |
|------|-------------|
| **1. Profile** | Scrapes the target company website and uses Claude to extract sector, description, technologies, geography, and strategic notes |
| **2. Prospect** | Claude generates a list of potential strategic and financial buyers based on the target profile |
| **3. Signals** | Searches each prospect for buy-side signals (recent acquisitions, stated expansion strategy, complementary products, etc.) via Exa |
| **4. Score** | Each prospect is scored across multiple dimensions with user-configurable weights; results are ranked |

Results are streamed back to the UI in real time via SSE. You can edit the target profile after Step 1 before continuing, and re-score at any time by adjusting weights.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11+, aiosqlite |
| AI | Anthropic Claude (claude-sonnet-4) |
| Search & Content | Exa API |
| Financial Data | FMP (Financial Modeling Prep) API |
| Scraping | httpx → curl_cffi → Playwright (progressive fallback) |
| Database | SQLite |

---


## Prerequisites

Ensure you have the following installed:

- Python 3.11+
- Node.js 18+ (with npm)
- Make (optional but recommended)
- API keys for Anthropic, Exa, and FMP

---

## Backend Setup (FastAPI)

The backend runs on **port 8000**.

### 1. Navigate to the backend directory

```bash
cd ma-prospecting-platform/backend

2. Create and activate a virtual environment
python -m venv venv

source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

3. Install dependencies
pip install -e ".[dev]"

4. (Optional) Enable Playwright for JS-heavy sites
pip install playwright
playwright install chromium

5. Configure environment variables
cp .env.example .env

Edit .env and fill in your API keys:

ANTHROPIC_API_KEY=your_anthropic_key
EXA_API_KEY=your_exa_key
FMP_API_KEY=your_fmp_key

6. Run the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Backend will be available at: http://localhost:8000
Interactive API docs at: http://localhost:8000/docs

Frontend Setup (Next.js)
The frontend runs on port 3000.

1. Navigate to the frontend directory
cd ma-prospecting-platform/frontend

2. Set up environment and install dependencies
cp .env.local.example .env.local
npm install

3. Start the development server
npm run dev
