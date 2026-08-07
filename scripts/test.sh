#!/usr/bin/env bash
#
# test.sh - Run tests
#

set -euo pipefail

export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=4096}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

MODE="${1:-all}"

case "${MODE}" in
    unit)
        echo "Running unit tests..."
        python -m pytest tests/ -v -m "not integration and not slow" --tb=short
        ;;

    integration|int)
        echo "Running integration tests..."
        python -m pytest tests/ -v -m "integration" --tb=short
        ;;

    e2e)
        cd frontend-react
        echo "Running E2E tests..."
        npm run test:e2e
        ;;

    frontend|fe)
        cd frontend-react
        echo "Running frontend tests..."
        npm test
        ;;

    coverage|cov)
        echo "Running tests with coverage..."
        python -m pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
        echo ""
        echo "HTML coverage report: file://${PROJECT_ROOT}/htmlcov/index.html"
        ;;

    quick|q)
        echo "Running quick test check (fail fast)..."
        python -m pytest tests/ -x -q --tb=line
        ;;

    all)
        echo "=== Running All Tests ==="
        python -m pytest tests/ -v --tb=short

        echo ""
        echo "=== Frontend Tests ==="
        cd frontend-react
        npm test
        cd ..
        ;;

    *)
        echo "Usage: $0 [unit|integration|e2e|frontend|coverage|quick|all]"
        echo ""
        echo "Modes:"
        echo "  unit            Run unit tests only"
        echo "  integration,int Run integration tests only"
        echo "  e2e             Run end-to-end tests"
        echo "  frontend, fe    Run frontend tests"
        echo "  coverage, cov   Run with coverage report"
        echo "  quick, q        Quick check (fail fast)"
        echo "  all             Run everything (default)"
        exit 1
        ;;
esac
