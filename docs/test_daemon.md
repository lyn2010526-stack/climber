# Continuous Test Daemon

Automated test daemon for the Agent Engine project that provides instant feedback on code changes.

## Architecture

```
scripts/
├── watch_tests.py          # Core daemon - file watcher + test runner
├── test_daemon.sh          # Start/stop/status/results CLI
├── test_daemon_alert.py    # Alert notification system
└── pre-commit.sh           # Pre-commit hook with test integration

.github/workflows/
└── test_daemon.yml         # CI/CD pipeline for test daemon

.test_daemon_alert_config.json  # Alert configuration
```

## Quick Start

```bash
# Start the daemon (runs in background)
./scripts/test_daemon.sh start

# Check status
./scripts/test_daemon.sh status

# View recent test results
./scripts/test_daemon.sh results

# View logs
./scripts/test_daemon.sh logs 100

# Stop the daemon
./scripts/test_daemon.sh stop

# Run full test suite once (no watching)
python scripts/watch_tests.py --full
```

## How It Works

### File Watching
- **Backend**: Monitors `*.py` files in project root (excluding `__pycache__`, `.git`, `node_modules`, etc.)
- **Frontend**: Monitors `*.ts`, `*.tsx`, `*.js`, `*.jsx`, `*.css` in `frontend-react/src/`
- **Debounce**: Rapid changes are debounced (1.5s delay) to avoid excessive test runs

### Test Execution
1. On file change, daemon identifies the matching test file
2. Runs targeted tests first (e.g., `app/config.py` -> `tests/test_config.py`)
3. Falls back to full quick suite if no matching test file found
4. Results are logged with PASS/FAIL status, test count, and duration

### Periodic Runs
- Every 10s x 6 = ~1 minute: Full backend quick test
- Every 10s x 30 = ~5 minutes: Coverage report generation
- Every 10s x 60 = ~10 minutes: E2E test run

### Alert System
- Console alerts with color-coded output
- Failure logs to `logs/test_failures.log`
- JSON results to `logs/test_daemon_results.json`
- Consecutive failure warnings (3+)
- Cooldown period (5 min) to prevent alert fatigue

### Coverage Tracking
- Generates HTML coverage reports in `htmlcov/`
- Tracks coverage trend over time
- Stores history in `logs/coverage_history.json`

## Configuration

### Alert Configuration (`.test_daemon_alert_config.json`)
```json
{
  "enabled": true,
  "webhook_url": null,
  "slack_webhook": null,
  "email_recipient": null,
  "consecutive_threshold": 3,
  "cooldown_seconds": 300
}
```

### Test Daemon CLI
```bash
scripts/test_daemon.sh start     # Start daemon
scripts/test_daemon.sh stop      # Stop daemon
scripts/test_daemon.sh restart   # Restart daemon
scripts/test_daemon.sh status    # Show status
scripts/test_daemon.sh logs [N]  # Show last N log lines
scripts/test_daemon.sh results   # Show test results table
```

### Python Daemon Options
```bash
python scripts/watch_tests.py              # Start watching
python scripts/watch_tests.py --full       # Run full suite once
python scripts/watch_tests.py --backend-only  # Watch backend only
python scripts/watch_tests.py --frontend-only # Watch frontend only
python scripts/watch_tests.py --no-periodic  # Disable periodic runs
```

## CI/CD Integration

### GitHub Actions (`.github/workflows/test_daemon.yml`)
- Runs on every PR to `main`/`develop`
- Full test suite with coverage
- Changed-file-targeted testing
- Coverage artifact upload
- Separate frontend test job

### Pre-commit Hook
- Lints staged Python files (ruff)
- Format check (ruff format)
- Type check (mypy)
- Runs related tests for changed files
- Frontend lint (oxlint)

Install:
```bash
pip install pre-commit
pre-commit install
```

Or manually:
```bash
ln -s ../../scripts/pre-commit.sh .git/hooks/pre-commit
```

## Output Files

| File | Description |
|------|-------------|
| `logs/test_daemon.log` | Full daemon output log |
| `logs/test_daemon_results.json` | JSON results of all test runs |
| `logs/test_failures.log` | Detailed failure logs |
| `logs/coverage_history.json` | Coverage trend data |
| `htmlcov/index.html` | HTML coverage report |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PYTHON` | `python3` | Python interpreter path |
| `APP_ENV` | - | Set to `testing` for test mode |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | - | Redis connection string |

## Troubleshooting

### Daemon won't start
- Check `logs/test_daemon.log` for errors
- Ensure Python 3.11+ is available
- Install dependencies: `pip install watchdog pytest pytest-cov`

### Tests timing out
- Default timeout is 120s per test run
- Reduce scope with `-m "not slow"` marker
- Check for import errors in the codebase

### No file changes detected
- Verify watched directories exist
- Check ignore patterns in script
- Ensure watchdog is installed: `pip install watchdog`
