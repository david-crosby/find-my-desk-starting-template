# DeskMate — Setup Guide

This guide covers everything needed to get DeskMate running locally from a clean clone.

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.12 | [python.org](https://python.org) or `pyenv install 3.12` |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| SQLite | any (bundled with Python) | — |

---

## 1. Clone and enter the project

```bash
git clone <repo-url>
cd find-my-desk-starting-template/DeskMate
```

---

## 2. Configure environment variables

Copy the example file and fill in the required values:

```bash
cp .env.example .env
```

Open `.env` and set:

### Required

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key. Get one at [console.anthropic.com](https://console.anthropic.com). The key starts with `sk-ant-`. |

### Optional (defaults work for local development)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/deskmate.db` | SQLite database path relative to the repo root. |
| `BACKEND_URL` | `http://localhost:8000` | URL the agent and UIs use to reach the backend API. |
| `AGENT_URL` | `http://localhost:8001` | URL the user UI uses to reach the agent server. |
| `AZURE_TENANT_ID` | — | Required only for real Microsoft Places integration (mocked in POC). |
| `AZURE_CLIENT_ID` | — | Required only for real Microsoft Places integration. |
| `AZURE_CLIENT_SECRET` | — | Required only for real Microsoft Places integration. |
| `ALLOCATION_RUN_TIME` | `23:00` | When the nightly allocation engine runs. |
| `CHECKIN_CUTOFF_TIME` | `10:00` | Cut-off time for marking no-shows and releasing desks. |

### Example `.env`

```env
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
DATABASE_URL=sqlite:///./data/deskmate.db
BACKEND_URL=http://localhost:8000
AGENT_URL=http://localhost:8001
```

---

## 3. Install dependencies

```bash
uv sync
```

This installs all workspace packages and their dependencies into `.venv`.

---

## 4. Initialise the database

```bash
uv run python scripts/init_db.py
```

This creates `data/deskmate.db` and all tables.

---

## 5. Seed demo data

```bash
uv run python scripts/seed_demo.py
```

This loads:
- 3 buildings (London, Leeds, Edinburgh)
- 6 floors, 24 sections, and ~138 desks
- 18 meeting rooms
- 10 demo users (engineers, designers, managers)
- Sample bookings for the current week
- Sample agent sessions

---

## 6. Start the services

Open three terminal windows (or use a process manager):

**Terminal 1 — Backend API (port 8000)**
```bash
uv run uvicorn places_backend.main:app --reload --port 8000
```

**Terminal 2 — AI Agent server (port 8001)**
```bash
uv run uvicorn places_agent.server:app --reload --port 8001
```

**Terminal 3 — User UI (port 8501)**
```bash
uv run streamlit run packages/ui_user/src/places_ui_user/app.py --server.port 8501
```

**Optional — Admin UI (port 8502)**
```bash
uv run streamlit run packages/ui_admin/src/places_ui_admin/app.py --server.port 8502
```

---

## 7. Open the app

| Service | URL |
|---|---|
| User UI (chat + booking) | http://localhost:8501 |
| Admin UI (floor plans, utilisation) | http://localhost:8502 |
| Backend API docs | http://localhost:8000/docs |
| Agent API docs | http://localhost:8001/docs |

---

## 8. Try it out

### Book a desk

1. Open http://localhost:8501
2. Select a user from the sidebar (e.g. Alice Chen)
3. Type: `Book me a quiet desk with a monitor for next Monday`
4. The agent will confirm the details and queue the booking

### Leave feedback

1. Go to **My Bookings** (sidebar)
2. Find a completed booking and click **Leave feedback via DeskMate**
3. The agent will ask for ratings and store the feedback

### Run the allocation engine manually

```bash
uv run python -m allocation.run
```

This processes all queued bookings for tomorrow and assigns desks.

---

## 9. Useful scripts

```bash
# Re-initialise the database (drops and recreates all tables)
uv run python scripts/init_db.py

# Re-seed demo data
uv run python scripts/seed_demo.py

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check .
uv run ruff format --check .
```

---

## Architecture overview

```
User UI (Streamlit :8501)
    |
    |--- chat messages ---> Agent Server (FastAPI :8001)
    |                           |
    |                           |--- tool calls ---> Backend API (FastAPI :8000)
    |                                                       |
    |--- direct API calls --------------------------------->|
                                                           |
                                                    SQLite (data/deskmate.db)
```

The agent uses the Anthropic Claude API (`claude-sonnet-4-6`) with:
- A cached system prompt (reduces token cost for multi-turn conversations)
- Tool use (function calling) to interact with the backend
- User context injection at session start (name, today's date)

---

## Troubleshooting

**"Could not reach the agent server"**
Make sure the agent server is running on port 8001:
```bash
uv run uvicorn places_agent.server:app --reload --port 8001
```

**"Backend not reachable" in the UI sidebar**
Make sure the backend API is running on port 8000:
```bash
uv run uvicorn places_backend.main:app --reload --port 8000
```

**Anthropic API errors (`AuthenticationError`)**
Check that `ANTHROPIC_API_KEY` in your `.env` is set to a valid key and that the `.env` file is in the `DeskMate/` directory (where you run `uv run` from).

**`ModuleNotFoundError: No module named 'places_core'`**
Run `uv sync` first to install all workspace packages.

**Empty user list in the UI sidebar**
The backend must be running and the database must be seeded. Run `uv run python scripts/seed_demo.py` then restart the backend.

---

## What is not built in this POC

- Production authentication (Microsoft Entra SSO is mocked with a sidebar dropdown)
- Multi-tenancy
- Mobile app
- Email delivery (notifications are console / webhook only)
- Full MS Places hardware integration (mocked with a webhook endpoint)
- The nightly allocation scheduler (APScheduler) is not wired up — run it manually with `uv run python -m allocation.run`
