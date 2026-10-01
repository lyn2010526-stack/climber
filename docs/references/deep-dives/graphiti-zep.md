# Zep / Graphiti 深挖（时序知识图谱记忆）

> 核验日期：2026-10-01。结论仅来自本会话已确认的仓库内文档（`docs/references/opensource-eval-42-50.md`「Zep 结论」、`docs/references/open-source-projects.md` #41）。本次未读取 Zep/Graphiti 源码，超出下文记录范围的内容一律标注"未核验"。

## 仓库状态/许可证

- Zep 主仓库 `https://github.com/getzep/zep` 当前明确声明它是 Zep Cloud 的示例、集成和工具仓库，不是 Zep 产品本体。
- Community Edition 已弃用并移入主仓库 `legacy/` 目录。
- 产品入口：`https://www.getzep.com/`；文档：`https://help.getzep.com/`。
- 开源时序知识图谱引擎：`https://github.com/getzep/graphiti`。
- 许可证：未核验（本次核验未记录 zep 与 graphiti 的 LICENSE 信息）。

## 源码入口与调用链（含 URL）

- 已确认入口（仓库定位层面）：
  - `https://github.com/getzep/zep` — 示例、集成、工具仓库；`legacy/` 存放已弃用的 Community Edition。
  - `https://github.com/getzep/graphiti` — 开源时序知识图谱引擎。
  - `https://www.getzep.com/` / `https://help.getzep.com/` — 产品与文档入口。
- Graphiti 内部源码入口与调用链：未核验（本次未克隆、未读取 graphiti 源码，具体模块划分、构建关系与调用路径均无证据）。

## 核心机制拆解

本次已确认的机制概念（均为借鉴方向，内部实现细节未核验）：

1. **时序事实有效期**：事实带时间属性并可过期，回答"某时刻什么为真"，对应 Climber 的时序衰减需求。
2. **关系召回**：按实体关系做图结构召回，与纯向量相似度检索互补。
3. **评估 harness**：记忆系统自带评估工具链，可衡量召回与有效性。
4. **运行形态**：Zep 为托管服务（Zep Cloud），Graphiti 可自托管；两者依赖边界不同。

上述三点的内部实现（图 schema、索引结构、衰减算法）未核验；本会话仅确认这些概念是 Climber 的借鉴方向。

## Climber 映射（引用本仓文件路径）

| Climber 模块 | 对应关系 |
| --- | --- |
| `app/core/profile/loop.py` | `ProfileLoopService._weight()` 指数时序衰减已落地，对应"事实有效期"的本地实现 |
| `app/core/memory/lifecycle.py` | write→index→retrieve→decay→forget→archive 全链路已实现，是 Graphiti 记忆生命周期的本地对照 |
| `app/core/vector_memory.py` | ChromaDB 语义检索后端；关系召回是当前缺口，图结构关联待补 |
| `app/core/integration/mem0_memory.py` | 已接入 Mem0 SDK 的向量+图存储，是图记忆的现有承载 |
| `app/core/profile/persistence.py` | 画像数据跨会话持久化承载（见 `docs/references/open-source-projects.md` 阶段 2） |

## 可借鉴/不采用结论

- **可借鉴**：事实有效期、关系召回、评估 harness 三个概念，作为画像与记忆参考项；先接入评估设计再决定运行形态。
- **待评估后决策**：托管服务依赖、数据边界、Graphiti 自托管成本三项需单独评估后才做接入决策。
- **不采用**：直接接入 Zep Cloud 托管服务（依赖与数据边界未评估）；已弃用的 Community Edition（已移入 `legacy/`，不再演进）。
- 阶段定位（见 `docs/references/open-source-projects.md` #41）：🔧 部分。

## 证据等级

| 记录内容 | 等级 |
| --- | --- |
| zep 主仓库定位、CE 弃用入 `legacy/`、产品/文档入口、graphiti 仓库地址 | 已核验（本会话公开页面确认，记录于 `docs/references/opensource-eval-42-50.md`） |
| Climber `app/core/profile/loop.py`、`app/core/memory/lifecycle.py`、`app/core/vector_memory.py`、`app/core/integration/mem0_memory.py` 现状 | 已核验（本仓只读调研，记录于 `docs/references/open-source-projects.md`） |
| zep 与 graphiti 的许可证 | 未核验 |
| Graphiti 图 schema、时序/关系召回的内部实现、评估 harness 具体形态 | 未核验 |
