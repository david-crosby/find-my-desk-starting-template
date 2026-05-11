#!/usr/bin/env bash
set -euo pipefail

echo "==> Initialising database..."
python scripts/init_db.py

echo "==> Starting backend API (port 8000)..."
uvicorn places_backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 2

echo "==> Starting agent server (port 8001)..."
uvicorn places_agent.server:app --host 0.0.0.0 --port 8001 --reload &
AGENT_PID=$!

sleep 1

echo "==> Starting user UI (port 8501)..."
streamlit run packages/ui_user/src/places_ui_user/app.py --server.port 8501 &
UI_USER_PID=$!

echo "==> Starting admin UI (port 8502)..."
streamlit run packages/ui_admin/src/places_ui_admin/app.py --server.port 8502 &
UI_ADMIN_PID=$!

echo ""
echo "All services running:"
echo "  Backend API : http://localhost:8000/docs"
echo "  Agent       : http://localhost:8001/docs"
echo "  User UI     : http://localhost:8501"
echo "  Admin UI    : http://localhost:8502"
echo ""
echo "Press Ctrl+C to stop everything."

trap "echo 'Stopping...'; kill $BACKEND_PID $AGENT_PID $UI_USER_PID $UI_ADMIN_PID 2>/dev/null || true" EXIT INT TERM
wait
