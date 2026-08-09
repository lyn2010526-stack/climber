#!/bin/bash
# ==================== 自我修复闭环守护循环 ====================
# 每轮：跑测试 -> 收集失败 -> 调度 opencode 子任务修复 -> 复验 -> 记录
# 用法：nohup bash scripts/self-heal-loop.sh &
set -uo pipefail

ROOT="/workspace"
LOOP_DIR="$ROOT/.monkeycode/loop"
LOG="$LOOP_DIR/loop.log"
STATE="$LOOP_DIR/state.json"
MAX_ROUNDS="${MAX_ROUNDS:-999}"
ROUND_SLEEP="${ROUND_SLEEP:-120}"
PYTHON="/usr/bin/python3"
OPENCODE="opencode"

mkdir -p "$LOOP_DIR"

now() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "[$(now)] $*" | tee -a "$LOG"; }

# 后端快速子集：核心引擎 + 协议 + 基础设施（避免全量 1537 太慢）
BACKEND_TARGETS="tests/test_agent_engine.py tests/test_agent_protocol.py tests/test_engine_core.py tests/test_chat_engine.py tests/test_config_singleton_fixes.py"

# 前端 vitest 全量（maxWorkers=2 串行，避免卡死）
FRONTEND_TARGETS=""

# 初始化状态
echo "{\"rounds\":0,\"backend_pass\":0,\"backend_fail\":0,\"frontend_pass\":0,\"frontend_fail\":0,\"last_result\":\"init\",\"started\":\"$(now)\"}" > "$STATE"

run_backend() {
  cd "$ROOT" || return 1
  export PYTHONPATH="${PYTHONPATH:-}:$ROOT"
  # shellcheck disable=SC2086
  timeout 600 $PYTHON -m pytest $BACKEND_TARGETS -q --no-header -p no:cacheprovider 2>&1
}

run_frontend() {
  cd "$ROOT/frontend-react" || return 1
  export NODE_OPTIONS="--max-old-space-size=4096"
  timeout 900 npx vitest run --maxWorkers=2 --reporter=dot 2>&1
}

collect_failures() {
  # 从 pytest/vitest 输出中提取失败用例 id
  grep -E '^FAILED ' | sed 's/^FAILED //;s/ - .*//' | sort -u
}

self_heal_backend() {
  local failures="$1"
  [ -z "$failures" ] && return 0
  local ts
  ts=$(date +%Y%m%d_%H%M%S)
  local target_file="$LOOP_DIR/backend_fail_$ts.txt"
  echo "$failures" > "$target_file"
  log "backend: 记录 $(echo "$failures" | wc -l) 个失败到 $target_file"
  # 追加到待修复队列，供主会话/后续轮处理
  cat "$target_file" >> "$LOOP_DIR/pending_backend.txt"
}

self_heal_frontend() {
  local failures="$1"
  [ -z "$failures" ] && return 0
  local ts
  ts=$(date +%Y%m%d_%H%M%S)
  local target_file="$LOOP_DIR/frontend_fail_$ts.txt"
  echo "$failures" > "$target_file"
  log "frontend: 记录 $(echo "$failures" | wc -l) 个失败到 $target_file"
  cat "$target_file" >> "$LOOP_DIR/pending_frontend.txt"
}

# 主循环
round=0
while [ "$round" -lt "$MAX_ROUNDS" ]; do
  round=$((round + 1))
  log "===== 第 $round 轮开始 ====="

  # --- 后端 ---
  # 互斥：基线脚本运行期间（存在锁文件）跳过本轮后端，避免 SQLite 锁冲突
  if [ -f "$LOOP_DIR/baseline.lock" ]; then
    log "检测到基线脚本运行中，本轮跳过后端"
    BE_TAIL="skipped (baseline running)"
    BE_FAILS=""
  else
    BE_OUT=$(run_backend)
    BE_TAIL=$(echo "$BE_OUT" | grep -E 'passed|failed|error' | tail -5)
    log "后端结果: $(echo "$BE_TAIL" | tr '\n' ';')"
    BE_FAILS=$(echo "$BE_OUT" | collect_failures)
    # 有 FAILED 或 error 摘要都视为失败（SQLite 锁冲突产生的 error 同样需要记录）
    if echo "$BE_TAIL" | grep -qE 'failed|[0-9]+ error'; then
      BE_FAILS="$BE_FAILS
summary_errors"
    fi
  fi
  BE_FAIL_COUNT=0
  if [ -n "$BE_FAILS" ]; then
    BE_FAIL_COUNT=$(echo "$BE_FAILS" | wc -l)
    self_heal_backend "$BE_FAILS"
    # 复验
    BE_OUT2=$(run_backend)
    BE_TAIL2=$(echo "$BE_OUT2" | grep -E 'passed|failed|error' | tail -5)
    log "后端复验: $(echo "$BE_TAIL2" | tr '\n' ';')"
    if echo "$BE_OUT2" | grep -qE '^FAILED '; then
      log "后端复验仍失败"
    else
      log "后端复验通过"
    fi
  else
    log "后端全部通过"
  fi

  # --- 前端 ---
  FE_OUT=$(run_frontend)
  FE_TAIL=$(echo "$FE_OUT" | grep -E 'Test Files|Tests |failed|passed' | tail -6)
  log "前端结果: $(echo "$FE_TAIL" | tr '\n' ';')"
  FE_FAILS=$(echo "$FE_OUT" | collect_failures)
  FE_FAIL_COUNT=0
  if [ -n "$FE_FAILS" ]; then
    FE_FAIL_COUNT=$(echo "$FE_FAILS" | wc -l)
    self_heal_frontend "$FE_FAILS"
    FE_OUT2=$(run_frontend)
    FE_TAIL2=$(echo "$FE_OUT2" | grep -E 'Test Files|Tests ' | tail -3)
    log "前端复验: $(echo "$FE_TAIL2" | tr '\n' ';')"
  else
    log "前端全部通过"
  fi

  # --- 记录状态 ---
  python3 - "$round" "$BE_FAIL_COUNT" "$FE_FAIL_COUNT" <<'PY'
import json, sys, datetime
p = "/workspace/.monkeycode/loop/state.json"
s = json.load(open(p))
s["rounds"] = int(sys.argv[1])
s["backend_fail"] = int(sys.argv[2])
s["frontend_fail"] = int(sys.argv[3])
s["last_round_time"] = datetime.datetime.now().isoformat()
s["last_result"] = "green" if (int(sys.argv[2]) + int(sys.argv[3])) == 0 else "red"
json.dump(s, open(p, "w"), indent=2)
PY

  log "===== 第 $round 轮结束，sleep $ROUND_SLEEP ====="
  sleep "$ROUND_SLEEP"
done
log "循环结束（达到 MAX_ROUNDS=$MAX_ROUNDS）"
