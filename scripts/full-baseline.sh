#!/bin/bash
# ==================== 分批可信全量测试基线 ====================
# 逐文件带超时跑，生成真实失败清单，避免整批卡死
# 用法：bash scripts/full-baseline.sh > .monkeycode/loop/full_baseline.log 2>&1
set -uo pipefail
cd /workspace || exit 1
export PYTHONPATH=/workspace
mkdir -p /workspace/.monkeycode/loop

RUN_ID="$(date +%Y%m%d_%H%M%S)"
RESULT_DIR="/workspace/.monkeycode/loop/baseline/$RUN_ID"
mkdir -p "$RESULT_DIR"

# 锁文件：告知 self-heal-loop 跳过后端，避免 SQLite 锁冲突
LOCK="/workspace/.monkeycode/loop/baseline.lock"
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "已有基线任务运行中: $LOCK" >&2
  exit 2
fi
trap 'flock -u 9' EXIT

echo "===== 分批全量基线 $(date) ====="
PASS=0
FAIL=0
SKIP=0
ERROR=0
FAILED_LIST="$RESULT_DIR/failed.txt"
: > "$FAILED_LIST"

for f in tests/test_*.py; do
  base=$(basename "$f" .py)
  out="$RESULT_DIR/$base.txt"
  echo "--- $f ---"
  timeout 300 python3 -m pytest "$f" -q --no-header -p no:cacheprovider --timeout=60 2>&1 | tee "$out" | grep -E "passed|failed|error|Timeout" | tail -3
  test_status=${PIPESTATUS[0]}
  summary=$(grep -E "passed|failed|error" "$out" | tail -1 || true)
  if [ "$test_status" -eq 124 ]; then
    echo "$base: timed out after 300 seconds" >> "$FAILED_LIST"
  elif [ "$test_status" -ne 0 ]; then
    echo "$base: ${summary:-pytest exited with status $test_status}" >> "$FAILED_LIST"
  elif [ -z "$summary" ]; then
    echo "$base: pytest produced no result summary" >> "$FAILED_LIST"
  fi
done

echo ""
echo "===== 汇总 ====="
echo "总文件: $(ls tests/test_*.py | wc -l)"
echo "--- 失败文件 ---"
cat "$FAILED_LIST" 2>/dev/null
echo ""
echo "--- 全部通过的文件 ---"
for f in tests/test_*.py; do
  base=$(basename "$f" .py)
  if ! grep -q "$base:" "$FAILED_LIST" 2>/dev/null; then
    echo "  PASS $base"
  fi
done
echo "===== 完成 $(date) ====="

if [ -s "$FAILED_LIST" ]; then
  exit 1
fi
