#!/usr/bin/env bash
#
# ci.sh - Run CI checks locally
#

set -euo pipefail

export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=4096}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "Running CI checks locally..."
echo "=============================="
echo ""

# 1. Lint
echo "[1/5] Linting..."
ruff check . --output-format=github
echo ""

# 2. Format check
echo "[2/5] Format check..."
ruff format --check .
echo ""

# 3. Type check
echo "[3/5] Type checking..."
mypy app/ --ignore-missing-imports --show-error-codes
echo ""

# 4. Tests
echo "[4/5] Running tests..."
python -m pytest tests/ -v --cov=app --cov-report=term-missing --tb=short
echo ""

# 5. Frontend
echo "[5/5] Frontend checks..."
cd frontend-react
npm run lint
npm run typecheck
npm test
cd ..
echo ""

echo "=============================="
echo "All CI checks completed!"
