# NeighbourLink

**Your neighbourhood, connected.** — Windows desktop community marketplace (rentals + local assistance).

## Stack

- **Desktop:** Electron, React, TypeScript, Vite
- **API:** Python, FastAPI, PostgreSQL, PostGIS
- **Security:** Argon2id, JWT sessions, Electron context isolation

## Current progress

- **Phase 1–3:** Auth, rentals (bookings, pay sandbox, condition reports, map), assistance (jobs, ratings, messages, skill admin)
- **Phase 4:** In-app notifications, wishlists (see `docs/PHASE4.md`)
- **Phase 5:** Community posts (see `docs/PHASE5.md`)
- **Phase 6:** Settings — locale, map defaults, notification prefs, change password (see `docs/PHASE6.md`)
- **Phase 7:** Identity verification, disputes, admin audit (see `docs/PHASE7.md`)
- **Phase 8:** Rental messages, mentorship, session revoke (see `docs/PHASE8.md`)
- **Phase 9:** Deposit escrow + HI/MR shell i18n (see `docs/PHASE9.md`)
- **Phase 10:** Community comments, reactions, moderation (see `docs/PHASE10.md`)
- **Ops:** `/ready`, request logging, Windows toasts, `apps/desktop` → `npm run dist:win`

## Prerequisites

- Node.js 20+
- Python **3.11 or 3.12** recommended (3.14 may need to compile some dependencies)
- Docker Desktop (for PostgreSQL + PostGIS)

## Quick start

### 1. Database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ..\.env.example ..\.env
alembic upgrade head
python -m app.seed_roles
python -m app.seed_categories
uvicorn app.main:app --host 127.0.0.1 --port 8742 --reload
```

### 3. Desktop app

```bash
cd apps/desktop
npm install
npm run dev
```

API docs (dev): http://127.0.0.1:8742/docs

## Project layout

```
neighbourlm/
├── apps/desktop/     # Electron + React UI
├── backend/          # FastAPI API
├── docker-compose.yml
└── docs/
```

## Roadmap

See `docs/PHASE1.md` and the product master spec in project planning docs.
