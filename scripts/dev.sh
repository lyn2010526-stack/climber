#!/usr/bin/env bash
#
# dev.sh - Start development servers
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }

cd "${PROJECT_ROOT}"

# Parse arguments
MODE="${1:-all}"

case "${MODE}" in
    backend|be)
        info "Starting backend development server..."
        source venv/bin/activate 2>/dev/null || true
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
        ;;

    frontend|fe)
        info "Starting frontend development server..."
        cd frontend-react
        npm run dev
        ;;

    all)
        info "Starting both backend and frontend..."
        info "Backend: http://localhost:8000"
        info "Frontend: http://localhost:5173"
        info "API Docs: http://localhost:8000/docs"
        echo ""

        # Start backend in background
        source venv/bin/activate 2>/dev/null || true
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info &
        BACKEND_PID=$!

        # Start frontend in background
        (cd frontend-react && npm run dev) &
        FRONTEND_PID=$!

        # Cleanup on exit
        trap 'kill ${BACKEND_PID} ${FRONTEND_PID} 2>/dev/null || true' EXIT INT TERM

        wait
        ;;

    *)
        echo "Usage: $0 [backend|frontend|all]"
        echo ""
        echo "Modes:"
        echo "  backend, be   Start only backend server"
        echo "  frontend, fe  Start only frontend server"
        echo "  all           Start both (default)"
        exit 1
        ;;
esac
