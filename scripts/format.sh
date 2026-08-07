#!/usr/bin/env bash
#
# format.sh - Format code
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

MODE="${1:-all}"

case "${MODE}" in
    python|py)
        echo "Formatting Python files..."
        ruff format .
        ;;

    check)
        echo "Checking Python formatting..."
        ruff format --check .
        ;;

    frontend|fe)
        cd frontend-react
        echo "Formatting frontend files..."
        npx prettier --write "src/**/*.{ts,tsx,css,json}"
        ;;

    all)
        echo "=== Formatting Python ==="
        ruff format .

        echo ""
        echo "=== Formatting Frontend ==="
        cd frontend-react
        npx prettier --write "src/**/*.{ts,tsx,css,json}" 2>/dev/null || echo "Frontend formatting skipped"
        cd ..
        ;;

    *)
        echo "Usage: $0 [python|frontend|check|all]"
        echo ""
        echo "Modes:"
        echo "  python, py    Format Python files"
        echo "  frontend, fe  Format frontend files"
        echo "  check         Check formatting without modifying"
        echo "  all           Format everything (default)"
        exit 1
        ;;
esac
