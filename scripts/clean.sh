#!/usr/bin/env bash
#
# clean.sh - Clean build artifacts and caches
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

echo "Cleaning Climber Agent Engine build artifacts..."
echo ""

# Python cache files
echo "Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Build artifacts
echo "Removing build artifacts..."
rm -rf build/ dist/ *.egg-info
rm -rf .mypy_cache/ .ruff_cache/ .pytest_cache/
rm -rf htmlcov/ .coverage coverage.xml

# Frontend build artifacts
if [ -d "frontend-react" ]; then
    echo "Removing frontend build artifacts..."
    rm -rf frontend-react/dist/
    rm -rf frontend-react/build/
    rm -rf frontend-react/coverage/
    rm -rf frontend-react/playwright-report/
    rm -rf frontend-react/test-results/
fi

# Docker artifacts
echo "Removing Docker build cache..."
rm -rf .docker/

# Logs
echo "Removing log files..."
find logs/ -type f -name "*.log" -delete 2>/dev/null || true

echo ""
echo "Clean complete!"
echo ""
echo "To fully clean (including virtual environment and node_modules):"
echo "  rm -rf venv/"
echo "  rm -rf frontend-react/node_modules/"
