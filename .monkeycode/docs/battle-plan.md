# Climber Agent Platform — 作战地图

> 目标：参考 50 个顶级开源项目，把所有功能做深，代码打到 50 万行，全端 UI 仿 iOS 精致风，
> 所有 bug 闭环，不重复造轮子、优先引入顶级开源库。

创建时间：2026-08-06

## 0. 当前状态快照

| 维度 | 现状 |
|---|---|
| 后端 Python | ~9.6 万行 / 479 文件 |
| 前端 React+TS | ~1395 源文件 |
| 核心依赖 | FastAPI + SQLAlchemy + ChromaDB + sentence-transformers（全自研，无 langchain/langgraph） |
| 测试基线 | 后端 103 文件 / 前端 vitest |
| 已知债务 | pregel 与 state_graph 双轨并存、记忆系统 8 处分散、成对重复文件、批量生成痕迹、空壳 TODO |

---

## 1. 50 个顶级开源参考项目清单

按领域分 8 类，每个项目标注「可借鉴点」和「可复用库」：

### 1.1 Agent 运行时 / 编排（核心参考）
1. **opencode** (anomalyco/opencode) — CLI Agent 工程的交互范式：流式输出、工具审批、多模型切换
2. **LangChain** (langchain-ai/langchain) — LCEL 链式组合、回调体系、Tool 抽象契约
3. **LangGraph** (langchain-ai/langgraph) — 状态图、SuperStep、断点/HITL、可直接复用替换自研 pregel
4. **Pydantic-AI** (pydantic/pydantic-ai) — 类型安全的 Agent 定义、结构化输出、可观测性
5. **CrewAI** (crewAIInc/crewAI) — 多角色协作、任务委派、层级流程
6. **AutoGen** (microsoft/autogen) — 多 Agent 对话、代码执行沙箱、群体协商
7. **DSPy** (stanfordnlp/dspy) — 提示/微调一体化、编译器式优化
8. **Dify** (langgenius/dify) — 工作流可视化编排、RAG 管道、Agent 策略模式
9. **Coze/扣子** (coze-dev/coze-studio) — 插件生态、知识库、工作流、多模态 Agent 全家桶
10. **Letta** (letta-ai/letta) — 记忆分层（core/archival/working）、ArchivalPassage 式持久记忆

### 1.2 状态图 / 工作流引擎
11. **Temporal** (temporalio/temporal-sdk-python) — 持久化执行、Saga、Timer、Signal
12. **Inngest** (inngest/inngest-py) — 事件驱动步骤函数、幂等、重试
13. **Windmill** (windmill-labs/windmill) — 脚本→工作流、App UI 生成、审批流
14. **Prefect** (PrefectHQ/prefect) — 任务编排、缓存、状态事件
15. **dagster** (dagster-io/dagster) — 数据编排、资源/IO Manager、分区

### 1.3 记忆与向量 / RAG
16. **LlamaIndex** (run-llama/llama_index) — RAG 管道、Query Engine、Agent Memory
17. **Haystack** (deepset-ai/haystack) — 模块化 RAG、Pipeline、评估
18. **RAGFlow** (infiniflow/ragflow) — 深度文档解析、表格/图片 OCR、知识图谱
19. **Qdrant** (qdrant/qdrant) — 高性能向量库（替代/补充 ChromaDB 生产部署）
20. **Mem0** (mem0ai/mem0) — 用户级记忆、自动提取/合并、图记忆
21. **Zep** (getzep/zep) — 会话级记忆、时间窗、事实提取

### 1.4 工具 / MCP / 插件
22. **Anthropic MCP** (modelcontextprotocol/servers) — MCP 标准协议、工具注册
23. **Composio** (composiohq/composio) — 500+ 集成、OAuth、动作编排
24. **LangChain Hub** (langchain-ai/langchain) — 提示/工具/Agent 注册中心
25. **Open Interpreter** (openinterpreter/open-interpreter) — 本地代码执行沙箱
26. **E2B** (e2b-dev/E2B) — 云端沙箱、文件系统隔离、多语言
27. **Modal** (modal-labs/modal) — Serverless GPU、函数即服务

### 1.5 前端 / UI / 交互
28. **Open WebUI** (open-webui/open-webui) — Chat UI、多模型、工作流、管道
29. **Chatwoot** (chatwoot/chatwoot) — 多渠道收件箱、实时聊天、分配
30. **Appsmith** (appsmithorg/appsmith) — 低代码内部工具、可视化查询/表单
31. **Reflex** (reflex-dev/reflex) — Python 全栈、AI 模板生态
32. **Shadcn/ui** (shadcn-ui/ui) — 开源组件系统、CVA 变体、主题 token
33. **Radix UI** (radix-ui/primitives) — 无样式原语、WAI-ARIA 完整
34. **Vaul** (emilkowalski/vaul) — iOS 风格抽屉
35. **Sonner** (emilkowalski/sonner) — iOS 风格 toast
36. **Framer Motion** (framer/motion) — 手势/布局动画、AnimatePresence
37. **Lenis** (darkroomengineering/lenis) — 丝滑滚动
38. **Aha-Spellter** (aharen-assistant/aha-claw) — 移动端 AI 界面参考

### 1.6 后端 / 平台工程
39. **Supabase** (supabase/supabase) — Auth、Realtime、Storage、Edge Function
40. **NocoDB** (nocodb/nocodb) — Airtable 替代、多视图、API 自动生成
41. **N8N** (n8n-io/n8n) — 节点式工作流、钩子、表达式
42. **Windmill** (windmill-labs/windmill) — 前端脚本驱动、类型安全客户端
43. **Infrahub** (opsmill/infrahub) — GraphQL + 版本化图数据库

### 1.7 安全 / 合规 / 沙箱
44. **E2B** (e2b-dev/E2B) — 隔离沙箱、多语言运行时
45. **gVisor** (google/gvisor) — 应用内核沙箱（深度隔离参考）
46. **OPA** (open-policy-agent/opa) — Rego 策略语言、细粒度权限

### 1.8 可观测性 / 评测
47. **LangSmith** (langchain-ai/langsmith-sdk) — Tracing、评测、Dataset
48. **Helicone** (helicone/helicone) — LLM 可观测、缓存、速率
49. **OpenLLMetry** (traceloop/openllmetry) — OTel 标准化 LLM 监控
50. **PromptFoo** (promptfoo/promptfoo) — LLM 红队/评测/CI

---

## 2. 功能深化路线图（8 大域）

### 2.1 核心 Agent 运行时（最高优先）
- **Pregel 主线接入**：收敛 state_graph/pregel_loop 双轨，以 `core/engine/pregel/` 为基准接入 AgentEngine 的 ReAct 循环
- **LangGraph 兼容层**：提供 LangGraph 式 StateGraph Builder API（可选直接嵌入 langgraph 库）
- **ReAct → Plan-Act-Reflect 升级**：Planner/Executor/Reviewer 三阶段
- **多模型路由**：按任务难度、成本、延迟自动选模型（参考 Aha-Spellter/LangChain）
- **子 Agent 编排**：Supervisor + Worker 层级（参考 AutoGen）

### 2.2 记忆系统（从 8 处收敛）
- 分层记忆：Working / Episodic / Semantic / Procedural / Archival（参考 Letta + Mem0）
- 自动提取/合并：每次会话结束自动提取事实（参考 Mem0）
- 图记忆：实体-关系-事实三元组（参考 Zep + Mem0 Graph）
- 长期/短期/工作记忆统一服务 `UnifiedMemoryService`
- 向量库可插拔：ChromaDB（本地）↔ Qdrant（生产）↔ pgvector

### 2.3 工作流与编排
- 可视化 DAG 编辑器（参考 Dify + N8N + xyflow/react 已集成）
- 事件驱动步骤（参考 Inngest）
- 持久化执行 + 断点续跑（参考 Temporal）
- 审批流 / Human-in-the-Loop（参考 Windmill）

### 2.4 工具与插件生态
- MCP 全套深化（已部分完成）：OAuth、健康检查、动态注册、插件市场
- 工具注册中心（参考 LangChain Hub + Composio）
- 500+ 第三方集成（Slack/GitHub/Notion/Jira/...）
- E2B/自研沙箱双轨执行

### 2.5 多 Agent 协作
- 三模式深化：Sequential / Hierarchical / Group Chat
- CrewAI 兼容的 Role/Goal/Backstory 抽象
- 任务委派 + 结果聚合 + 辩论协商（参考 AutoGen）
- Agent 间通信协议（A2A protocol 已有骨架）

### 2.6 安全与合规
- OPA/Rego 策略引擎
- 多层沙箱（进程 → gVisor → E2B 云端）
- 权限矩阵 + 审批工作流
- 审计日志 + 敏感数据脱敏

### 2.7 可观测与评测
- LangSmith 兼容 Tracing（OTel 标准化）
- LLM 红队 + 自动评测（参考 PromptFoo）
- 成本/延迟/质量三轴监控
- 会话回放与标注

### 2.8 平台化
- 多租户 + RBAC（参考 Supabase Auth）
- 计费/配额/速率限制（参考 Helicone）
- 提示/Agent/工作流 注册中心与版本管理
- Webhook / Event Bus / 异步任务队列深化

---

## 3. 前端仿 iOS 精致化方案

### 3.1 设计系统统一
- **收敛双 token 体系**：以 `index.css @theme` 为唯一权威，删除 `tokens.css` 冗余
- **色彩**：iOS 风格语义色（systemBlue/systemGreen/systemRed/...）+ 玻璃拟态层级
- **字体**：SF Pro 风格层级（largeTitle/title/body/caption）+ 动态字重
- **圆角**：iOS 标准（10/12/16/20/连续曲率 continuous corner）
- **阴影**：多层柔和投影（umbra/penumbra/ambient 三轴）

### 3.2 组件库重构
- 废弃老 `components/` 旧体系，统一迁移到 `components/ui/` 新体系
- 引入 **Radix UI** 原语（Dialog/Tooltip/Dropdown/Sheet/Tabs/...）
- 引入 **shadcn/ui** 风格组件（已具备 cva + cn 基础）
- 引入 **Vaul**（iOS 抽屉）、**Sonner**（iOS toast）
- 引入 **Framer Motion**（手势、布局动画、AnimatePresence）
- 引入 **Lenis**（丝滑滚动）
- 清理 `extreme/ultra/ultra_mega/massive/super` 测试目录与 `.bak` 文件

### 3.3 动效与交互
- 页面转场：iOS 风格 push/pop/slide（framer-motion layoutAnimation）
- 微交互：按钮涟漪、开关弹簧、列表重排序（drag-to-reorder）
- 手势：滑动返回、长按菜单、下拉刷新、双指缩放
- 加载态：Skeleton shimmer（非 spinner）+ 渐进式内容揭示
- 手势驱动的 Sheet/Drawer（参考 iOS 控制中心）

### 3.4 架构升级
- 手写 hash 路由 → **React Router v7**（已安装未使用）
- 状态管理统一：Zustand store 命名规范化（清理 PascalCase/snake_case 混用）
- 数据获取：TanStack Query 深化（缓存/预取/乐观更新）
- 国际化：i18next 补全所有面板 + 中/英/日/韩

### 3.5 页面全覆盖
- 55+ 页面逐一 iOS 化重设计
- 新增：记忆管理面板、工具市场、工作流可视化编辑器、Agent 编排画布、
  评测中心、多租户管理、计费中心、通知中心、设置中心
- 移动端：Capacitor（已集成）→ iOS/Android 原生壳

---

## 4. 开源库引入清单（不重复造轮子）

| 领域 | 当前 | 引入/替换为 | 理由 |
|---|---|---|---|
| Agent 编排 | 自研 ReAct | **LangGraph** 或兼容层 | 状态图/HITL/断点事实标准 |
| 结构化输出 | 手写 | **Pydantic-AI** | 类型安全、生态成熟 |
| 记忆 | 8 处分散自研 | **Mem0** + 自研 UnifiedMemoryService | 自动提取/合并/图记忆 |
| 向量库 | ChromaDB | +**Qdrant** (生产可插拔) | 高性能、生产级 |
| 工作流 | 自研 AST | **Windmill** 风格或 **Prefect** | 持久化执行、事件驱动 |
| 沙箱 | 自研 | +**E2B** (云端) | 多语言、隔离 |
| 策略权限 | 手写 | **OPA/Rego** | 细粒度、声明式 |
| 可观测 | 手写 | **OpenLLMetry** (OTel) + **Helicone** 风格 | 标准化、LLM 专属 |
| 评测 | 无 | **PromptFoo** | LLM 红队/CI |
| 前端组件 | 双体系手写 | **Radix** + **shadcn/ui** | 可访问性 + 主题系统 |
| 动画 | 纯 CSS | **Framer Motion** + **Lenis** | 手势/布局/丝滑滚动 |
| 路由 | hash 手写 | **React Router v7** | 已安装、标准化 |
| 抽屉/Toast | 手写 | **Vaul** + **Sonner** | iOS 原生感 |
| 移动端 | Capacitor | 保留 + **Ionic** 风格组件 | 原生壳已有 |
| 表单 | 手写 | **React Hook Form** + **Zod** | 类型安全校验 |
| 表格 | 手写 | **TanStack Table** | 大数据虚拟化 |
| 图表 | Recharts | 保留 + 补 **Visx** 定制 | 基础足够 |

---

## 5. Bug 闭环与测试策略

- 当前后端 103 测试文件基线运行中（全绿目标）
- 前端 vitest 144 passed 基线
- 自修复循环 `scripts/self-heal-loop.sh` 后台持续运行
- 新增功能必须 TDD：先写测试再实现
- 集成测试：关键链路（Agent 运行、记忆读写、工作流执行、沙箱隔离）必须有 e2e
- 代码覆盖率目标：后端 ≥70%、前端 ≥60%

---

## 6. 代码体积策略（→ 50 万行）

当前 9.6 万行 Python + 前端。50 万行 = 扩大约 5 倍。**不盲目堆量，通过功能深化自然增长**：

- 后端各域深化（Agent/记忆/工作流/工具/安全/评测/平台化）预计新增 15-20 万行
- 前端 55+ 页面 iOS 化 + 500+ 组件 + 多端预计新增 10-15 万行
- 测试覆盖率提升新增 5-8 万行
- 文档/配置/脚本/CI 新增 2-3 万行
- 引入 LangGraph/Mem0/OPA 等顶级库增加集成层 3-5 万行

**质量优先**：每个模块必须有明确职责、测试覆盖、无重复。

---

## 7. 执行阶段

### Phase 1：基线闭环 + 架构收敛（当前）
- [x] 后端测试全绿
- [ ] 收敛 pregel 双轨
- [ ] 清理重复文件与空壳
- [ ] 引入 LangGraph + Pydantic-AI

### Phase 2：Agent 运行时深化
- [ ] Pregel 主线接入 AgentEngine
- [ ] ReAct → Plan-Act-Reflect 升级
- [ ] 多模型路由
- [ ] 子 Agent Supervisor

### Phase 3：记忆系统统一
- [ ] UnifiedMemoryService
- [ ] 分层记忆（5 层）
- [ ] Mem0 集成
- [ ] 图记忆

### Phase 4：前端 iOS 化
- [ ] 设计系统统一
- [ ] Radix + shadcn/ui + Framer Motion 引入
- [ ] 路由/状态/动效重构
- [ ] 55+ 页面逐一重设计

### Phase 5：工作流 + 工具生态
- [ ] 可视化 DAG 编辑器
- [ ] MCP 生态深化
- [ ] 500+ 集成

### Phase 6：安全 + 评测 + 可观测
- [ ] OPA 策略引擎
- [ ] E2B 沙箱双轨
- [ ] OpenLLMetry 监控
- [ ] PromptFoo 评测

### Phase 7：平台化 + 移动端
- [ ] 多租户 RBAC
- [ ] 计费/配额
- [ ] Capacitor iOS/Android 原生发布
- [ ] 注册中心与版本管理

---

## 8. 关键原则

1. **不重复造轮子**：自研前先查 50 参考项目，有顶级 OSS 直接引入
2. **TDD**：新功能先写测试
3. **收敛优先于新增**：先清理双轨/重复，再叠加新能力
4. **UI 质量 ≥ 功能数量**：每个面板都必须是 iOS 级精致
5. **持续绿色**：基线运行期间任何合并必须保持全绿
