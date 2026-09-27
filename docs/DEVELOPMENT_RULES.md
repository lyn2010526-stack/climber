# Climber 开发规则

## 1. 事实边界

- 默认后端是 Python 3.11+、FastAPI、SQLAlchemy、Pydantic 和 pytest。
- `app/api/` 处理 API 表面，`app/core/` 处理 Agent 核心，`app/models/`、`app/storage/`、`app/tools/`、`app/workflow/` 和 `app/multi_agent/` 按职责归位。
- `app/static/` 当前只有少量 HTML，属于轻量 Web 表面。
- `frontend-react/` 是独立的 React 前端目录。任务没有明确前端扩展时，不修改它，也不引入新的前端技术栈。
- 仓库没有 uni-app 实现；文档、计划和代码禁止把 uni-app 当成既有事实。

## 2. 六步开发方法的项目化规则

### 第一步：先定风格和 Token

UI 任务必须先阅读 `docs/DESIGN_SYSTEM.md`，写明目标表面、信息层级、交互状态、响应式边界和无障碍要求。先确定语义 Token，再写页面和组件。后端任务先确定 API、领域、存储和安全边界，避免把业务逻辑塞进路由函数。

### 第二步：组件库决策只在前端扩展时执行

涉及 `app/static/` 的小型 HTML 改动时，优先使用已有 HTML/CSS 结构和 Token。涉及 `frontend-react/` 的规模化 UI 扩展时，才评估现有组件、候选库、许可证、包体积、可访问性、主题能力和测试成本。决策写入任务文档或 PR 描述，并先完成一个代表性组件验证。

### 第三步：目录归位

新增文件必须放入职责目录，并在提交前检查归属：

- API 路由与 schema：`app/api/`、`app/schemas/`。
- Agent 执行、安全、权限、会话和核心服务：`app/core/`。
- 模型适配和领域编排：`app/models/`、`app/workflow/`、`app/multi_agent/`。
- 持久化和迁移：`app/storage/`、`alembic/`。
- 外部集成和工具：`app/integrations/`、`app/tools/`。
- 测试：`tests/`；前端测试留在 `frontend-react` 的既有测试目录。
- 规则与说明：根目录 `AGENTS.md`、`docs/`、`.monkeycode/`。

### 第四步：重复组件和重复逻辑必须复用

发现第二处相同结构或相同规则时，先寻找现有实现。重复的 API 校验、权限判断、错误响应、Token、UI 组件和测试 fixture 应抽取到稳定的共享边界。只有行为确实不同，或抽取会增加不合理耦合时，才保留局部实现，并在代码评审中说明原因。

### 第五步：文档索引同步

新增或重命名文档时同步更新本节的“相关文档与来源”索引。API、架构、部署、开发、测试、安全和设计规则分别归入对应主题；文档只描述已验证的仓库事实或明确标注为提案。链接必须指向真实路径或官方来源。

### 第六步：开发前后自检

开发前检查工作树、目标边界、依赖和测试入口。开发后检查 `git diff --check`、文件归属、文档索引、测试结果和未覆盖范围。任务声明必须区分“已执行”“失败”“跳过”和“未验证”。

## 3. 验证门禁

按变更范围执行最小充分验证，并记录实际命令：

```bash
# Python lint and formatting check
ruff check app tests
ruff format --check app tests

# Python tests; use the repository timeout option unless an explicit override is required
python3 -m pytest tests/ -q

# Optional type check when typed modules are changed
mypy app/
```

当前仓库的 `pyproject.toml` 定义了 pytest `--timeout=120` 默认参数，`ruff.toml` 会覆盖
`pyproject.toml` 的 Ruff 配置发现结果。修改 Ruff 规则时同步检查两份配置；安全规则和
测试规则以实际执行的 `ruff --show-settings`/lint 输出为准。安全门禁回归可先运行：

```bash
python3 -m pytest tests/core/test_secret_key_validation.py tests/core/test_auth_escalation.py tests/core/test_default_admin_security.py tests/core/test_ssrf_enforcement.py tests/core/test_network_egress_gate.py tests/core/test_emergency_stop_enforcement.py tests/core/test_emergency_stop_wiring.py tests/core/test_layer_import_boundaries.py -q -o addopts='' -p no:cacheprovider
```

前端扩展时，在 `frontend-react/` 使用项目现有脚本运行 lint、类型检查、构建、Vitest 和 Playwright；先读取 `frontend-react/package.json`，不得凭记忆声明脚本存在。UI 变更还要执行适用的浏览器检查或快照审阅。

验证规则：

- 不得在未运行命令时声明“测试通过”“lint 通过”“构建成功”或“快照已更新”。
- 失败命令必须保留失败原因和影响范围；禁止用删测试、静默跳过或盲目更新快照制造伪绿。
- 测试应覆盖正常路径、边界、错误路径和安全敏感路径；API 改动应包含契约或集成测试。
- 修改安全、权限、网络出口、认证和数据迁移时，验证优先级高于局部格式优化。
- 测试依赖外部服务时使用 mock、fixture 或显式 opt-in；凭据只能由用户项目环境变量提供，禁止写入文档和代码。
- 文档中的测试数量、风险状态和能力声明必须带日期或命令来源；历史测试报告不能替代当前运行结果。

## 4. Agent 协作与文件边界

任务按根目录 `AGENTS.md` 的 8 个子任务边界拆分。每个 Agent 领取前声明：目标、文件集合、依赖、验证命令和交接产物。文件集合发生变化时先更新声明。公共接口由生产代码责任边界和测试责任边界共同复核；文档和治理改动由边界 8 维护，并引用真实来源。

协作期间保留用户或其他 Agent 的未提交改动。当前任务禁止自动 commit、push 或重写历史；提交由用户单独决定。

## 5. 反模式清单

- 在 FastAPI 项目中虚构 uni-app、移动端目录、组件或脚本。
- 为一次小型 HTML 改动直接引入 UI 框架。
- 在多个路由、页面或测试中复制同一业务规则。
- 将临时脚本、生成文件、截图或构建产物混入源目录。
- 用未经执行的命令、过期报告或主观观察支撑完成声明。
- 通过修改无关模块、放宽全局 lint、删除测试或更新快照绕过验证。

## 6. 相关文档与来源

- Agent 入口：`AGENTS.md`
- 设计系统：`docs/DESIGN_SYSTEM.md`
- 文档索引：本文件的“相关文档与来源”章节
- 安全审计：`SECURITY_AUDIT_REPORT.md`
- 死代码与能力事实对账：`docs/DEAD_CODE_DOCUMENTATION_AUDIT.md`
- 测试结果记录：`docs/TEST_REPORT.md`
- 依赖与供应链审计：`docs/DEPENDENCY_AUDIT.md`
- 贡献流程：`CONTRIBUTING.md`
- Python 风格：`docs/STYLE_GUIDE.md`
- FastAPI 官方文档：https://fastapi.tiangolo.com/
- pytest 官方文档：https://docs.pytest.org/en/stable/
- Ruff 官方文档：https://docs.astral.sh/ruff/
- OpenAI Cookbook Agent 指南：https://github.com/openai/openai-cookbook/blob/main/AGENTS.md
- GitHub CODEOWNERS 规范：https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
