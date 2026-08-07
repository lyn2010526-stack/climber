#!/usr/bin/env bash
#
# pre-commit.sh - Pre-commit hook with test daemon integration
#
# Install with: pre-commit install
# Or manually: ln -s ../../scripts/pre-commit.sh .git/hooks/pre-commit
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=true
STAGED_PY_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)
STAGED_FE_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ts|tsx|js|jsx)$' || true)

echo "Running pre-commit checks..."
echo ""

# 1. Lint staged Python files
if [ -n "${STAGED_PY_FILES}" ]; then
    echo -e "${YELLOW}[1/4] Ruff lint (Python)...${NC}"
    if ! echo "${STAGED_PY_FILES}" | xargs ruff check; then
        echo -e "${RED}  Lint failed${NC}"
        PASS=false
    else
        echo -e "${GREEN}  Lint passed${NC}"
    fi
    echo ""
fi

# 2. Format check staged Python files
if [ -n "${STAGED_PY_FILES}" ]; then
    echo -e "${YELLOW}[2/4] Format check (Python)...${NC}"
    if ! echo "${STAGED_PY_FILES}" | xargs ruff format --check; then
        echo -e "${RED}  Format check failed${NC}"
        PASS=false
    else
        echo -e "${GREEN}  Format passed${NC}"
    fi
    echo ""
fi

# 3. Type check staged Python files
if [ -n "${STAGED_PY_FILES}" ]; then
    echo -e "${YELLOW}[3/4] Type check (mypy)...${NC}"
    if ! echo "${STAGED_PY_FILES}" | xargs mypy --ignore-missing-imports --show-error-codes; then
        echo -e "${RED}  Type check failed${NC}"
        PASS=false
    else
        echo -e "${GREEN}  Type check passed${NC}"
    fi
    echo ""
fi

# 4. Run related tests for staged files
if [ -n "${STAGED_PY_FILES}" ]; then
    echo -e "${YELLOW}[4/4] Running related tests...${NC}"

    TEST_FILES=""
    for f in ${STAGED_PY_FILES}; do
        if [[ "$f" == app/* ]]; then
            STEM=$(basename "$f" .py)
            CANDIDATE="tests/test_${STEM}.py"
            if [ -f "${CANDIDATE}" ]; then
                TEST_FILES="${TEST_FILES} ${CANDIDATE}"
            fi
        fi
    done

    if [ -n "${TEST_FILES}" ]; then
        echo "  Found test files: ${TEST_FILES}"
        if ! python -m pytest ${TEST_FILES} -x -q --tb=line --no-header -m "not integration and not slow"; then
            echo -e "${RED}  Tests failed${NC}"
            PASS=false
        else
            echo -e "${GREEN}  Tests passed${NC}"
        fi
    else
        echo "  No matching test files found (skipping)"
    fi
    echo ""
fi

# 5. Frontend checks
if [ -n "${STAGED_FE_FILES}" ] && [ -d "frontend-react" ]; then
    echo -e "${YELLOW}[Frontend] Lint staged files...${NC}"
    cd frontend-react

    if ! echo "${STAGED_FE_FILES}" | xargs npx oxlint 2>/dev/null; then
        echo -e "${YELLOW}  Frontend lint warning (non-blocking)${NC}"
    else
        echo -e "${GREEN}  Frontend lint passed${NC}"
    fi
    cd ..
    echo ""
fi

# Final result
if [ "${PASS}" = true ]; then
    echo -e "${GREEN}All pre-commit checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Pre-commit checks failed. Fix issues before committing.${NC}"
    exit 1
fi
