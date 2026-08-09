#!/bin/bash
# ==================== 分批可信全量测试基线 ====================
# 逐文件带超时跑，生成真实失败清单，避免整批卡死
# 用法：bash scripts/full-baseline.sh > .monkeycode/loop/full_baseline.log 2>&1
set -uo pipefail
cd /workspace || exit 1
export PYTHONPATH=/workspace
mkdir -p /workspace/.monkeycode/loop

RESULT_DIR="/workspace/.monkeycode/loop/baseline"
rm -rf "$RESULT_DIR"
mkdir -p "$RESULT_DIR"

# 锁文件：告知 self-heal-loop 跳过后端，避免 SQLite 锁冲突
LOCK="/workspace/.monkeycode/loop/baseline.lock"
trap 'rm -f "$LOCK"' EXIT
touch "$LOCK"

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
  summary=$(grep -E "passed|failed|error" "$out" | tail -1 || true)
  # 解析摘要
  if [ -n "$summary" ] && echo "$summary" | grep -q "failed"; then
    echo "$base: $summary" >> "$FAILED_LIST"
  fi
  if [ -n "$summary" ] && echo "$summary" | grep -q "error"; then
    echo "$base: $summary" >> "$FAILED_LIST"
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
