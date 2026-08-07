#!/usr/bin/env bash
#
# lint.sh - Run linting tools
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

MODE="${1:-all}"

case "${MODE}" in
    python|py)
        echo "Running ruff linter..."
        ruff check .
        ;;

    python-fix|py-fix)
        echo "Running ruff linter with auto-fix..."
        ruff check --fix .
        ;;

    frontend|fe)
        cd frontend-react
        echo "Running ESLint..."
        npm run lint
        ;;

    frontend-fix|fe-fix)
        cd frontend-react
        echo "Running ESLint with auto-fix..."
        npx eslint . --fix
        ;;

    all)
        echo "=== Python Linting ==="
        ruff check .

        echo ""
        echo "=== Frontend Linting ==="
        cd frontend-react
        npm run lint
        cd ..
        ;;

    *)
        echo "Usage: $0 [python|python-fix|frontend|frontend-fix|all]"
        echo ""
        echo "Modes:"
        echo "  python, py         Lint Python files"
        echo "  python-fix, py-fix Lint and auto-fix Python files"
        echo "  frontend, fe       Lint frontend files"
        echo "  frontend-fix, fe-fix Lint and auto-fix frontend files"
        echo "  all                 Lint everything (default)"
        exit 1
        ;;
esac
