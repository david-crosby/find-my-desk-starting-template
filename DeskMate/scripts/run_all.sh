#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Load .env if present ────────────────────────────────────────────────────
if [[ -f "$ROOT/.env" ]]; then
    set -a
    # shellcheck source=/dev/null
    source "$ROOT/.env"
    set +a
fi

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
    echo "ERROR: ANTHROPIC_API_KEY is not set."
    echo "       Add it to $ROOT/.env or export it before running this script."
    exit 1
fi

# ── PYTHONPATH (Python 3.12 skips _editable_impl_*.pth files) ───────────────
export PYTHONPATH="\
$ROOT/packages/core/src:\
$ROOT/packages/backend/src:\
$ROOT/packages/agent/src:\
$ROOT/packages/ui_user/src:\
$ROOT/packages/ui_admin/src"

# ── Kill anything already on our ports ──────────────────────────────────────
for PORT in 8000 8001 8501 8502; do
    PIDS=$(lsof -ti :"$PORT" 2>/dev/null || true)
    if [[ -n "$PIDS" ]]; then
        echo "==> Freeing port $PORT..."
        echo "$PIDS" | xargs kill -9 2>/dev/null || true
    fi
done

# ── Initialise / migrate the database ───────────────────────────────────────
echo "==> Initialising database..."
cd "$ROOT"
uv run python scripts/init_db.py

# ── Seed demo data if the database is empty ─────────────────────────────────
ROW_COUNT=$(uv run python -c "
from places_core.db import SessionLocal
from places_core.models import User
db = SessionLocal()
print(db.query(User).count())
db.close()
" 2>/dev/null || echo "0")

if [[ "$ROW_COUNT" -eq 0 ]]; then
    echo "==> Seeding demo data..."
    uv run python scripts/seed_demo.py
else
    echo "==> Database already has data — skipping seed."
fi

# ── Start services ───────────────────────────────────────────────────────────
echo "==> Starting backend API     (port 8000)..."
uv run uvicorn places_backend.main:app --host 0.0.0.0 --port 8000 --reload \
    > "$ROOT/logs/backend.log" 2>&1 &
BACKEND_PID=$!

sleep 2

echo "==> Starting agent server    (port 8001)..."
uv run uvicorn places_agent.server:app --host 0.0.0.0 --port 8001 --reload \
    > "$ROOT/logs/agent.log" 2>&1 &
AGENT_PID=$!

sleep 1

echo "==> Starting user UI         (port 8501)..."
uv run streamlit run \
    "$ROOT/packages/ui_user/src/places_ui_user/app.py" \
    --server.port 8501 --server.headless true \
    > "$ROOT/logs/ui_user.log" 2>&1 &
UI_USER_PID=$!

echo "==> Starting admin UI        (port 8502)..."
uv run streamlit run \
    "$ROOT/packages/ui_admin/src/places_ui_admin/app.py" \
    --server.port 8502 --server.headless true \
    > "$ROOT/logs/ui_admin.log" 2>&1 &
UI_ADMIN_PID=$!

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo "  Backend API : http://localhost:8000/docs"
echo "  Agent       : http://localhost:8001/docs"
echo "  User UI     : http://localhost:8501"
echo "  Admin UI    : http://localhost:8502"
echo ""
echo "Logs → $ROOT/logs/"
echo "Press Ctrl+C to stop everything."

trap "echo ''; echo 'Stopping...'; kill $BACKEND_PID $AGENT_PID $UI_USER_PID $UI_ADMIN_PID 2>/dev/null || true" EXIT INT TERM
wait
