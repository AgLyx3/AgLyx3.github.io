#!/usr/bin/env bash
# Start local backend (port 8000) and frontend server (port 3000) for development/testing.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "Starting backend on http://localhost:8000 ..."
cd "$ROOT/backend"
.venv/bin/uvicorn app.main:app --port 8000 --reload &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:3000 ..."
python3 -m http.server 3000 --directory "$ROOT/frontend" &
FRONTEND_PID=$!

trap "echo 'Stopping...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM

echo ""
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl-C to stop both servers."
wait
