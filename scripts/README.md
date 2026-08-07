#!/usr/bin/env bash
#
# Climber Agent Engine - Automation Scripts
#
# This file is a convenience wrapper that delegates to individual scripts.
# Run ./scripts/help.sh for usage information.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

show_help() {
    cat << 'EOF'
Climber Agent Engine - Development Scripts

Usage: ./scripts/<command.sh> [options]

Commands:
  setup.sh          Initialize development environment
  dev.sh            Start development servers (backend + frontend)
  check.sh          Run all checks (lint, format, typecheck, test)
  lint.sh           Run linting (ruff, mypy, eslint)
  format.sh         Format code (ruff format, prettier)
  typecheck.sh      Run type checking (mypy, tsc)
  test.sh           Run all tests
  clean.sh          Clean build artifacts and caches
  ci.sh             Run CI checks locally
  release.sh        Prepare a new release

Individual script help: ./scripts/<command.sh> --help
EOF
}

show_help
