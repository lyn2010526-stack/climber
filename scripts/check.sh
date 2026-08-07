#!/usr/bin/env bash
#
# check.sh - Run all checks (lint, format, typecheck, test)
#

set -euo pipefail

export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=4096}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASS=0
FAIL=0

info() { echo -e "\n${BLUE}=== $* ===${NC}"; }
success() { echo -e "${GREEN}[PASS]${NC} $*"; ((PASS++)); }
error() { echo -e "${RED}[FAIL]${NC} $*"; ((FAIL++)); }

cd "${PROJECT_ROOT}"

info "Running all checks for Climber Agent Engine"
echo "============================================"

# Python linting
info "Running ruff linter..."
if ruff check . ; then
    success "Ruff linting passed"
else
    error "Ruff linting failed"
fi

# Python formatting
info "Running ruff format check..."
if ruff format --check . ; then
    success "Format check passed"
else
    error "Format check failed - run './scripts/format.sh' to fix"
fi

# Python type checking
info "Running mypy type checker..."
if mypy app/ --ignore-missing-imports ; then
    success "Type checking passed"
else
    error "Type checking failed"
fi

# Backend tests
info "Running backend tests..."
if python3 -m pytest tests/ -x -q --tb=short ; then
    success "Backend tests passed"
else
    error "Some backend tests failed"
fi

# Frontend checks
if [ -d "frontend-react" ] && command -v npm &>/dev/null; then
    cd frontend-react

    info "Running frontend linter..."
    if npm run lint ; then
        success "Frontend linting passed"
    else
        error "Frontend linting failed"
    fi

    info "Running frontend type check..."
    if npm run typecheck ; then
        success "Frontend type checking passed"
    else
        error "Frontend type checking failed"
    fi

    cd ..
else
    info "Skipping frontend checks (npm not available or no frontend-react directory)"
fi

# Summary
echo ""
echo "============================================"
info "Results: ${PASS} passed, ${FAIL} failed"

if [ ${FAIL} -gt 0 ]; then
    echo -e "${RED}Some checks failed. Please fix the issues above.${NC}"
    exit 1
else
    echo -e "${GREEN}All checks passed!${NC}"
fi
