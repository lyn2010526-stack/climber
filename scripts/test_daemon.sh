#!/usr/bin/env bash
#
# test_daemon.sh - Start/stop the continuous test daemon
#
# Usage:
#   ./scripts/test_daemon.sh start    # Start daemon in background
#   ./scripts/test_daemon.sh stop     # Stop daemon
#   ./scripts/test_daemon.sh status   # Check daemon status
#   ./scripts/test_daemon.sh restart  # Restart daemon
#   ./scripts/test_daemon.sh logs     # View recent logs
#   ./scripts/test_daemon.sh results  # View test results
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PIDFILE="${PROJECT_ROOT}/.test_daemon.pid"
LOGFILE="${PROJECT_ROOT}/logs/test_daemon.log"
RESULTS_FILE="${PROJECT_ROOT}/logs/test_daemon_results.json"
ALERT_LOG="${PROJECT_ROOT}/logs/test_failures.log"

# Ensure logs directory exists
mkdir -p "${PROJECT_ROOT}/logs"

start_daemon() {
    if [ -f "${PIDFILE}" ] && kill -0 "$(cat "${PIDFILE}")" 2>/dev/null; then
        echo "Test daemon already running (PID: $(cat "${PIDFILE}"))"
        return 0
    fi

    echo "Starting continuous test daemon..."
    echo "  Log: ${LOGFILE}"

    cd "${PROJECT_ROOT}"
    PYTHON_CMD="${PYTHON:-python3}"
    nohup "${PYTHON_CMD}" -u scripts/watch_tests.py >> "${LOGFILE}" 2>&1 &
    echo $! > "${PIDFILE}"

    sleep 1
    if kill -0 "$(cat "${PIDFILE}")" 2>/dev/null; then
        echo "Daemon started (PID: $(cat "${PIDFILE}"))"
        echo "  Watch: ${PROJECT_ROOT}/app/ and ${PROJECT_ROOT}/frontend-react/src/"
    else
        echo "Failed to start daemon"
        rm -f "${PIDFILE}"
        return 1
    fi
}

stop_daemon() {
    if [ ! -f "${PIDFILE}" ]; then
        echo "No daemon running (no PID file found)"
        return 0
    fi

    local pid
    pid=$(cat "${PIDFILE}")

    if kill -0 "${pid}" 2>/dev/null; then
        echo "Stopping daemon (PID: ${pid})..."
        kill "${pid}"
        sleep 1

        if kill -0 "${pid}" 2>/dev/null; then
            echo "Force killing..."
            kill -9 "${pid}" 2>/dev/null || true
        fi

        rm -f "${PIDFILE}"
        echo "Daemon stopped."
    else
        echo "Daemon not running (stale PID file)"
        rm -f "${PIDFILE}"
    fi
}

daemon_status() {
    if [ -f "${PIDFILE}" ]; then
        local pid
        pid=$(cat "${PIDFILE}")
        if kill -0 "${pid}" 2>/dev/null; then
            echo "Daemon running (PID: ${pid})"
            echo "  Log: ${LOGFILE}"

            if [ -f "${RESULTS_FILE}" ]; then
                local total
                total=$(python3 -c "
import json
with open('${RESULTS_FILE}') as f:
    results = json.load(f)
print(len(results))
                " 2>/dev/null || echo "0")
                echo "  Test runs logged: ${total}"
            fi
            return 0
        fi
    fi
    echo "Daemon not running"
    return 1
}

view_logs() {
    if [ -f "${LOGFILE}" ]; then
        tail -n "${1:-50}" "${LOGFILE}"
    else
        echo "No log file found at ${LOGFILE}"
    fi
}

view_results() {
    if [ -f "${RESULTS_FILE}" ]; then
        python3 << 'PYEOF'
import json

results_file = "/workspace/agent-engine/logs/test_daemon_results.json"

try:
    with open(results_file) as f:
        results = json.load(f)
except Exception as e:
    print(f"Could not parse results file: {e}")
    exit(1)

if not results:
    print("No test results yet.")
    exit(0)

recent = results[-10:]
header = f"{'Time':<22} {'Backend':<8} {'Status':<6} {'Tests':<7} {'Fails':<7} {'Duration':<10} Trigger"
print(header)
print("-" * 100)
for r in recent:
    ts = r.get("timestamp", "")[:19]
    be = "Yes" if r.get("backend") else "No"
    status = "PASS" if r.get("passed") else "FAIL"
    tests = r.get("test_count", 0)
    fails = r.get("fail_count", 0)
    dur = f"{r.get('duration', 0):.2f}s"
    trigger = r.get("trigger", "unknown")[-40:]
    print(f"{ts:<22} {be:<8} {status:<6} {tests:<7} {fails:<7} {dur:<10} {trigger}")

total = len(results)
passed = sum(1 for r in results if r.get("passed"))
failed = total - passed
print(f"\nTotal runs: {total} | Passed: {passed} | Failed: {failed}")
PYEOF
    else
        echo "No results file found at ${RESULTS_FILE}"
    fi
}

case "${1:-start}" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        stop_daemon
        sleep 1
        start_daemon
        ;;
    status)
        daemon_status
        ;;
    logs)
        view_logs "${2:-50}"
        ;;
    results)
        view_results
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|results}"
        exit 1
        ;;
esac
