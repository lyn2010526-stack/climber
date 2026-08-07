# Development Standards Summary

> Climber Agent Engine - Quick reference for development standards and tools.

## Standards Overview

| Standard | Tool | Configuration |
|----------|------|---------------|
| Editor Config | EditorConfig | `.editorconfig` |
| Python Linting | ruff | `pyproject.toml` |
| Python Formatting | ruff format | `pyproject.toml` |
| Python Type Check | mypy | `pyproject.toml` |
| Frontend Lint | ESLint | `frontend-react/.eslintrc.json` |
| Frontend Format | Prettier | `frontend-react/.prettierrc` |
| Tests | pytest / vitest | `pyproject.toml` / `frontend-react/vite.config.ts` |
| Pre-commit | pre-commit | `.pre-commit-config.yaml` |

## Quick Commands

```bash
# Setup
./scripts/setup.sh

# Development
./scripts/dev.sh              # Start all services
./scripts/dev.sh backend      # Backend only
./scripts/dev.sh frontend     # Frontend only

# Checks
./scripts/check.sh            # All checks
./scripts/lint.sh             # Linting only
./scripts/format.sh           # Format code
./scripts/typecheck.sh        # Type checking only
./scripts/test.sh             # Run tests

# Utilities
./scripts/clean.sh            # Clean build artifacts
./scripts/ci.sh               # Run CI checks locally
./scripts/release.sh 1.2.0    # Prepare release
```

## Branch Naming

```
feature/<issue-id>-<description>
fix/<issue-id>-<description>
refactor/<issue-id>-<description>
docs/<description>
chore/<description>
```

## Commit Messages

```
<type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert
Scopes: api, core, auth, db, ui, tools, models, workflow, config, deps, ci
```

## Code Review Process

1. Create PR with filled template
2. Automated checks must pass
3. At least 1 approval required
4. Squash merge to main
