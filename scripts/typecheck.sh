#!/usr/bin/env bash
#
# typecheck.sh - Run type checking
#

set -euo pipefail

export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=4096}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

MODE="${1:-all}"

case "${MODE}" in
    python|py)
        echo "Running mypy type checker..."
        mypy app/ --ignore-missing-imports
        ;;

    frontend|fe)
        cd frontend-react
        echo "Running TypeScript compiler..."
        npm run typecheck
        ;;

    all)
        echo "=== Python Type Checking ==="
        mypy app/ --ignore-missing-imports

        echo ""
        echo "=== Frontend Type Checking ==="
        cd frontend-react
        npm run typecheck
        cd ..
        ;;

    *)
        echo "Usage: $0 [python|frontend|all]"
        echo ""
        echo "Modes:"
        echo "  python, py    Type check Python files"
        echo "  frontend, fe  Type check frontend files"
        echo "  all           Type check everything (default)"
        exit 1
        ;;
esac
