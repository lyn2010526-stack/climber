#!/usr/bin/env bash
# Package the ARC-Bench / GOSIM factory26 submission bundle for climber.
#
# Output zip layout:
#   climber-arcbench-<date>/
#     README.md
#     adapters/arcbench/main.py + agent_driver.py + prompts.py + acceptance.py
#     adapters/arcbench/app/headless/   (execution engine used by the driver)
#     adapters/arcbench/vendor/         (offline MIT-licensed runtime fallback)
#
# Entry point mirrors the official adapter contract:
#   python adapters/arcbench/main.py <requirement> --output-dir DIR \
#          --type web --app-type web --web-port N
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d)"
OUT_DIR="${ARCBENCH_PACK_DIR:-$ROOT/dist}"
WORK="$OUT_DIR/.pack-stage"
ARCHIVE="$OUT_DIR/climber-arcbench-$STAMP.zip"

command -v zip >/dev/null || { echo "zip is required"; exit 1; }
mkdir -p "$OUT_DIR"

find "$WORK" -delete 2>/dev/null || true
rm -rf "$WORK"
mkdir -p "$WORK/climber-arcbench-$STAMP"
DEST="$WORK/climber-arcbench-$STAMP"

mkdir -p "$DEST/adapters"
cp -R "$ROOT/adapters/arcbench" "$DEST/adapters/arcbench"
# Keep agent_driver's repo-relative `from app.headless import ...` valid:
# ship the headless engine at the pack root, mirroring the repo layout.
mkdir -p "$DEST/app"
cp -R "$ROOT/app/headless" "$DEST/app/headless"

find "$DEST" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$DEST" -name "*.pyc" -delete 2>/dev/null || true

printf '%s\n' \
  "# ARC-Bench adapter runtime. The vendored copy under vendor/ works offline;" \
  "# install the PyPI package when network access is available." \
  "arcbench-runtime>=0.1.0" > "$DEST/adapters/arcbench/requirements.txt"

python3 - "$DEST/README.md" <<'PYEOF'
from pathlib import Path
Path(__import__("sys").argv[1]).write_text(
    """# Climber ARC-Bench / GOSIM factory26 submission

Entry (official adapter contract), from inside the bundle:

    python adapters/arcbench/main.py <requirement_path> \
        --output-dir <out> --type web --app-type web --web-port <N>

The agent builds a complete web app under `<out>/frontend` (must `npm run
build` cleanly) and `<out>/backend` (must `npm start` on the `PORT` env),
commits to the output git repo, and emits `.arc/runner-events.jsonl` via the
ARC-Bench runtime SDK (PyPI `arcbench-runtime`; `vendor/` is an offline copy).

Independent GUI acceptance (`acceptance.py`) starts the deliverable backend
exactly the way the competition grader does (`PORT=<web_port>`, plus
`ARC_EXTRA_PORTS` when specs hard-code extra ports), runs the official
Playwright specs from `$ARCBENCH_TESTS_DIR` (fallback `/workspace/tests`),
attributes per-spec outcomes to requirement node ids mentioned in spec
titles/paths, and only then emits per-node `mark_test_passed` /
`mark_test_failed`. Nodes without spec evidence stay unverified: with no
machine-readable Playwright report the result is flagged as exit-code
attribution, and when the runner is absent the run records
"acceptance infra unavailable" instead of a fake pass. `mark_run_completed`
messages always state whether independent tests really ran.

Models come from the competition gateway env: OPENAI_BASE_URL /
OPENAI_API_KEY / MODEL. Tunables: CLIMBER_ARC_TIME_BUDGET (default 2700 s),
CLIMBER_ARC_NODE_TIMEOUT (1200 s), CLIMBER_ARC_ACCEPTANCE_TIMEOUT (900 s),
CLIMBER_ARC_SMOKE_PORT (3100). Python 3.10+; stdlib only beyond arcbench-runtime.
""",
    encoding="utf-8",
)
PYEOF

printf '%s\n' '"""ARC-Bench entry shim: `python main.py ...` at the bundle root."""' 'import os, runpy, sys' 'from pathlib import Path' 'target = Path(__file__).resolve().parent / "adapters" / "arcbench" / "main.py"' 'sys.argv[0] = str(target)' 'runpy.run_path(str(target), run_name="__main__")' > "$DEST/main.py"

for py in \
  "$DEST/adapters/arcbench/main.py" \
  "$DEST/adapters/arcbench/agent_driver.py" \
  "$DEST/adapters/arcbench/prompts.py" \
  "$DEST/adapters/arcbench/acceptance.py" \
  "$DEST/app/headless/cli.py" \
  "$DEST/app/headless/model.py" \
  "$DEST/app/headless/runner.py" \
  "$DEST/app/headless/workspace.py"; do
  python3 -m py_compile "$py"
done


(
  cd "$WORK"
  rm -f "$ARCHIVE"
  zip -qr "$ARCHIVE" "climber-arcbench-$STAMP"
)
find "$WORK" -type f -delete 2>/dev/null || true
find "$WORK" -depth -type d -exec rmdir {} + 2>/dev/null || true

echo "packed: $ARCHIVE"
unzip -l "$ARCHIVE" | tail -n 3
