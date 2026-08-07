# 开发者指南

## 环境

- Python 3.11+，Node.js 18+，SQLite（或 PostgreSQL），Redis 可选。
- 后端入口：`app/main.py`（FastAPI，DI 单例 `AgentEngine`）。
- 前端入口：`frontend-react/src/App.tsx`（React + Vite + Tailwind，Hash 路由）。

## 后端

### 安装与启动

```bash
cd /workspace/agent-engine
pip install --break-system-packages -r requirements.txt

# 本地（认证关闭）
ENABLE_AUTH=false uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`ENABLE_AUTH=false` 时由 Principal dependency 生成 `default-user`；认证启用时需提供稳定 `APP_SECRET_KEY`，缺失会快速失败。

### 静态检查

```bash
python3 -m compileall app -q
ruff check app
ruff check app/core/engine/pregel app/core/checkpoint.py ... # 按改动文件
```

### 测试

```bash
# 联合回归（六路核心，103 项）
python3 -m pytest tests/core/engine/pregel/test_runtime_hardening.py tests/test_checkpoint_session_persistence.py tests/test_checkpoint.py tests/test_multi_agent_unification.py tests/test_multi_agent.py tests/test_permission_controller.py tests/test_permission_tiers.py tests/test_runtime_infrastructure_fixes.py tests/test_principal_api_contracts.py tests/test_smoke_cases.py -q -p no:cacheprovider

# OpenAPI 契约（154 paths / 194 operations / operation ID 唯一）
python3 -c "from app.main import app; s=app.openapi(); ..."
```

全量收集与运行：`python3 -m pytest tests/ --collect-only -q`（约 6.2 万项）与 `python3 -m pytest tests/ -q -p no:cacheprovider`。无 `--timeout` 插件，不要传该参数。

### 已知环境注意

- `scripts/watch_tests.py` 会持续触发并发 pytest，与共享 SQLite 竞争锁；可信全量前先确认无并发 pytest。
- 测试文件必须使用 `AsyncClient` 异步写法。
- `tests/conftest.py` 的忽略列表已彻底移除；缺失模块的正确做法是在 `app/` 补齐，测试自身 bug 只记录清单不改断言。

## 前端

所有前端命令需放大内存：

```bash
cd /workspace/agent-engine/frontend-react
export NODE_OPTIONS="--max-old-space-size=4096"

npm run typecheck
npm run build
npm run lint          # oxlint

# 单元测试（380 文件 / 3305 项）；并发 worker 过多会卡死，建议限制
npm test -- --maxWorkers=2

# E2E（Playwright，webServer 自动拉起后端与 vite）
npm run test:e2e -- e2e/06-workspace-responsive.spec.ts
```

### 测试约定

- 单测语言 zh-CN（`src/test-setup.ts` 强制），e2e 语言 en（`e2e/helpers.ts`）。
- Playwright webServer 显式 `ENABLE_AUTH=false`，否则全部 `/api/v1/*` 返回 401。
- `navigateTo` 用 `window.location.hash` + `waitForTimeout`，避免 `networkidle` 挂起。
- `apiClient` 直接返回泛型数据，调用方禁止再次 `.ok`/`.json()`。

## 验收门禁

- 后端：compileall、ruff、OpenAPI operation ID 唯一、联合回归 + smoke。
- 前端：typecheck、生产 build、3305 项 Vitest、1440/768/375 三视口 Playwright（scrollWidth <= innerWidth、导航可达、按钮 >= 44px、键盘焦点）。
- 测试真实执行，禁止 skip、排除或修改断言伪造通过。

## 文档

- 规格：`.monkeycode/specs/2026-08-05-unified-agent-platform/`
- 项目文档：`.monkeycode/docs/`（INDEX/ARCHITECTURE/INTERFACES/API/DEPLOYMENT）
- 记忆：`.monkeycode/MEMORY.md`（构建、测试、排错与工作流知识）
