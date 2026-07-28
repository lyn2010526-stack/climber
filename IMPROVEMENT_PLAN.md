# Climber 改进计划

> 基于对代码库的全面审计，与 OpenClaw、AutoGPT、LangChain 等成熟项目的差距分析。
> 当前状态：项目无法运行（20+ 核心文件缺失）。

---

## 一、P0 — 致命问题（必须先解决才能运行）

### 1. 恢复缺失的核心文件

**问题**：20+ 核心文件缺失，应用启动即崩溃。

**缺失文件清单**：
- `app/config.py` — 被 7+ 模块导入
- `app/core/__init__.py` — 被 15+ 模块导入
- `app/api/v1/__init__.py` — 被 main.py 导入
- `app/api/v1/*.py` — 30+ 端点文件全部缺失
- `app/core/agent_engine.py` — 核心引擎
- `app/core/auto_loop.py` — 自动循环执行
- `app/core/mcp.py` — MCP 客户端
- `app/core/guardrails.py` — 护栏系统
- `app/core/compressor.py` — 上下文压缩
- `app/core/collab_prompts.py` — 协作提示词
- `app/core/cost_tracker.py` — 成本追踪
- `app/core/approval.py` — 审批流程
- `app/core/context_builder.py` — 上下文构建
- `app/core/enhanced_rag.py` — 增强 RAG
- `app/core/evaluation.py` — 评估系统
- `app/core/group_engine.py` — 群组引擎
- `app/core/checkpoint.py` — 检查点
- `app/core/branch_manager.py` — 分支管理
- `app/core/parallel.py` — 并行执行

**验收标准**：
```bash
cd agent-engine
python -c "from app.main import app"  # 不报错
uvicorn app.main:app --reload  # 服务正常启动
```

### 2. 修复数据库迁移

**问题**：`alembic/versions/` 空目录，无迁移脚本。

**行动**：
- 生成初始迁移脚本：`alembic revision --autogenerate -m "init"`
- 确保所有模型（25+ 张表）都有对应的迁移
- 测试：`alembic upgrade head` 从零开始建表成功

### 3. 修复 CORS 安全漏洞

**问题**：`allow_origins=["*"]` + `allow_credentials=True` = 严重安全漏洞

**修复**：
```python
# 当前（危险）
allow_origins=["*"]
allow_credentials=True

# 改为
allow_origins=["http://localhost:5173", "http://localhost:3000"]
allow_credentials=True
allow_methods=["GET", "POST", "PUT", "DELETE"]
allow_headers=["*"]
```

### 4. 修复认证系统

**问题**：
- API Key "加密"是 XOR 混淆，不是加密
- 自定义 JWT 实现不标准
- 默认游客模式，所有端点无保护

**修复**：
- 用 ` cryptography.fernet ` 替换 XOR
- 用 ` pyjwt ` 替换自定义 JWT
- 默认关闭游客模式，强制登录
- 实现 RBAC 角色权限

### 5. 修复代码注入漏洞

**问题**：`eval()` / `exec()` 在 workflow/engine.py 中可被绕过

**修复**：
- 移除 `eval()` / `exec()`，改用安全的模板引擎（Jinja2 sandboxed）
- 或限制为预定义函数集合

---

## 二、P1 — 高优（生产必备）

### 6. 部署基础设施

- [ ] 编写 `Dockerfile`（多阶段构建，Python + Node）
- [ ] 编写 `docker-compose.yml`（FastAPI + React + PostgreSQL + Redis）
- [ ] 编写 `.dockerignore`
- [ ] 编写 `Makefile`（common tasks）
- [ ] 配置 GitHub Actions CI/CD
- [ ] 编写 `.env.example`（所有环境变量说明）
- [ ] 编写 `deploy.sh`（一键部署脚本）

### 7. 项目基础文件

- [ ] 编写 `CONTRIBUTING.md`
- [ ] 编写 `SECURITY.md`（漏洞报告流程）
- [ ] 编写 `CHANGELOG.md`
- [ ] 添加 `LICENSE` 文件（MIT）
- [ ] 完善 `README.md`（区分"已实现"和"规划中"）

### 8. 测试体系

**当前**：15% 文件覆盖率，无安全测试

**目标**：核心模块 80% 覆盖率

**行动**：
- [ ] 补充 `test_auth.py`（认证/加密测试）
- [ ] 补充 `test_security_sandbox.py`（沙箱测试）
- [ ] 补充 `test_mcp_client.py`（MCP 客户端测试）
- [ ] 补充 `test_api_endpoints.py`（API 端点测试）
- [ ] 补充 `test_e2e_chat.py`（端到端对话测试）
- [ ] 补充前端测试（覆盖 50% 组件）
- [ ] 添加安全测试（路径遍历、命令注入、XSS）
- [ ] 添加性能测试（并发 100 用户）

### 9. 可观测性

- [ ] 集成 Sentry（错误追踪）
- [ ] 实现分布式链路追踪（OpenTelemetry）
- [ ] 配置结构化 JSON 日志（生产环境）
- [ ] 添加健康检查端点（`/health` 不崩溃）
- [ ] 配置 Prometheus + Grafana 监控
- [ ] 添加告警规则（错误率、延迟、资源使用率）

### 10. 消息队列与任务调度

**问题**：任务调度在内存中，重启丢失

**修复**：
- [ ] 集成 Celery + Redis（异步任务队列）
- [ ] 实现死信队列（失败任务重试）
- [ ] 实现任务持久化（数据库存储任务状态）
- [ ] 实现定时任务（Cron）

---

## 三、P2 — 中优（用户体验）

### 11. 前端稳定性

- [ ] 添加 SSE/WebSocket 重连逻辑
- [ ] 添加请求取消（AbortController）
- [ ] 添加加载骨架屏（所有页面）
- [ ] 添加离线支持（Service Worker）
- [ ] 添加错误边界（每个页面路由）
- [ ] 修复内存泄漏（useEffect cleanup）

### 12. 前端功能

- [ ] 添加深色/浅色主题切换
- [ ] 集成 i18n 国际化框架
- [ ] 添加响应式布局（移动端适配）
- [ ] 添加服务端渲染（SSR）或静态生成（SSG）

### 13. 性能优化

- [ ] 前端路由懒加载
- [ ] 图片懒加载和优化
- [ ] API 请求缓存（React Query / SWR）
- [ ] 数据库查询优化（N+1 问题）
- [ ] 添加 Redis 缓存层（热点数据）

---

## 四、P3 — 长期迭代（对标 OpenClaw）

### 14. 核心功能补齐

- [ ] 多模型自动降级（OpenAI → Anthropic → Ollama）
- [ ] 并发熔断/限流（Circuit Breaker）
- [ ] 定时任务（Cron jobs）
- [ ] 任务断点续跑（Checkpoint/Restore）
- [ ] 浏览器自动化（Playwright）
- [ ] 桌面键鼠操控（PyAutoGUI）
- [ ] 批量任务队列
- [ ] 多密钥轮询
- [ ] 请求失败自动重试（指数退避）

### 15. 远程控制

- [ ] 手机网页远程访问
- [ ] Telegram/微信 Bot 集成
- [ ] 外网访问鉴权（VPN / 内网穿透）
- [ ] 多设备会话同步

### 16. 插件生态

- [ ] 插件市场（Plugin Marketplace）
- [ ] 插件热加载（已实现基础版，需完善）
- [ ] 插件版本管理
- [ ] 插件依赖解析

### 17. 安全加固

- [ ] OS 级沙箱（Docker / nsjail）
- [ ] 分层权限（用户/管理员/只读）
- [ ] 高危操作人工审批
- [ ] 文件路径白名单
- [ ] 命令前缀白名单
- [ ] 网络访问控制（出站过滤）
- [ ] 审计日志（所有操作可追溯）
- [ ] 敏感数据脱敏

### 18. 打包分发

- [ ] 一键打包 Windows exe（PyInstaller / Electron）
- [ ] 一键打包 macOS dmg
- [ ] 一键打包 Linux AppImage
- [ ] 自动更新机制

---

## 五、工程治理

### 19. 代码质量

- [ ] 统一代码风格（Ruff / Black / Prettier）
- [ ] 添加类型检查（mypy / tsc）
- [ ] 添加预提交钩子（pre-commit）
- [ ] 重构全局单例（依赖注入）
- [ ] 消除循环导入
- [ ] 添加模块文档字符串
- [ ] 添加函数文档字符串

### 20. 版本管理

- [ ] 使用 Semantic Versioning
- [ ] 打 v0.1.0 tag（最小可用版本）
- [ ] 维护 CHANGELOG
- [ ] 发布 Release Notes

---

## 六、路线图

### Phase 0：能跑起来（1-2 周）
- 恢复 20+ 缺失文件
- 修复数据库迁移
- 修复 CORS 和认证
- 编写 Dockerfile + docker-compose
- 编写 requirements.txt + .env.example
- 实现最小 main.py（/health + /chat）

**验收**：`docker compose up` 后浏览器能对话

### Phase 1：单 Agent 闭环（2-4 周）
- 实现模型适配层（LiteLLM）
- 实现 ReAct 循环（Think → Tool → Observe）
- 实现 3 个基础工具（shell、file_read/write、web_fetch）
- 实现两层记忆（会话 + 长期）
- 收缩 API 到 5 个

**验收**：Agent 能读文件、写文件、回复总结

### Phase 2：安全沙箱 + 记忆（1-2 月）
- OS 级沙箱（Docker / nsjail）
- 三层记忆落地（工作/短期/长期）
- 向量数据库集成（Chroma/Qdrant）
- 遗忘机制

**验收**：Agent 在沙箱中安全执行，记忆持久化

### Phase 3：多智能体编排（2-3 月）
- DAG 工作流引擎
- 2 种协作模式（辩论式、层级式）
- 3 种推理策略（ToT、Self-Refine、Debate）
- React Flow 可视化

**验收**：多 Agent 协作完成复杂任务

### Phase 4：差异化（持续）
- MCP / A2A 协议支持
- 可观测黑匣子（完整 ReAct 日志）
- 插件市场
- 一键打包客户端

---

## 七、当前优先级建议

**不是"改 2000 个点"，是"先让项目跑起来"**。

本周必须完成：
1. 从 git history 恢复缺失文件
2. 验证 `python -c "from app.main import app"` 能通过
3. 验证 `uvicorn app.main:app --reload` 能启动
4. 验证前端 `npm run dev` 能访问
5. 验证 `/health` 返回 200

**如果这些都无法完成，说明项目需要从零重建，不是补功能。**

---

## 八、与 OpenClaw 的核心差距总结

| 维度 | OpenClaw | Climber（当前） | 差距 |
|------|----------|----------------|------|
| 可用性 | 一键 exe，开箱即用 | 无法运行 | ⭐⭐⭐⭐⭐ |
| 部署 | 单文件 | 需 Python + Node + 数据库 | ⭐⭐⭐⭐⭐ |
| 文档 | 完整 + 社区 | 仅有骨架 | ⭐⭐⭐⭐ |
| 测试 | 1000+ 测试 | 15% 覆盖率 | ⭐⭐⭐⭐ |
| 安全 | 分层沙箱 + 审批 | 无沙箱 + 游客模式 | ⭐⭐⭐⭐⭐ |
| 生态 | 海量插件 | 无 | ⭐⭐⭐⭐⭐ |
| 远程控制 | 原生支持 | 无 | ⭐⭐⭐⭐ |
| 稳定性 | 200+ 版本迭代 | 1 天 | ⭐⭐⭐⭐⭐ |

**结论**：Climber 目前是一个"骨架项目"，不是"产品"。需要先解决 P0 问题才能谈后续功能。
