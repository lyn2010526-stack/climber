# UI 研究报告：10 个开源 AI 平台的设计模式分析

> 生成日期: 2026-08-04
> 目标项目: /workspace/agent-engine (Climber)

---

## 1. LobeChat / LobeHub

**仓库**: lobehub/lobehub | **Stars**: 81.2k | **技术栈**: Next.js, Zustand, TailwindCSS

### UI 设计特点

| 维度 | 特点 |
|------|------|
| 布局 | 三栏布局：左侧会话列表 + 中央聊天区 + 右侧配置面板 |
| 配色 | 深色渐变主题，紫色/蓝色主色调，毛玻璃效果 |
| 交互 | 消息气泡支持悬停操作、插件触发器、Agent 广场 |

### 可复用模式

1. **消息气泡操作栏**: hover 时浮现复制/编辑/重新生成/引用/删除
2. **插件触发器**: 输入框中 `@` 触发插件选择器
3. **Agent 广场**: 卡片式 Agent 市场，支持一键安装
4. **会话分组**: 按时间/标签分组管理会话

### 应用到 Climber

- 消息气泡增加 hover 操作栏（已有基础，需增强动画和布局）
- 插件市场页面改为卡片式布局
- 输入框增加 `@` 触发器支持工具/插件快速调用

---

## 2. Open WebUI

**仓库**: open-webui/open-webui | **Stars**: 147.8k | **技术栈**: Svelte, TailwindCSS

### UI 设计特点

| 维度 | 特点 |
|------|------|
| 布局 | 可折叠侧栏 + 全宽聊天区 + 右侧工作区 |
| 配色 | 中性灰绿配色，简洁专业 |
| 交互 | 模型选择器悬浮面板、知识库 `#` 快捷引用 |

### 可复用模式

1. **模型选择器**: 顶部下拉面板展示模型能力标签
2. **知识库引用**: `#知识库名` 语法快速引用
3. **多模态输入**: 文件/图片拖拽上传区域
4. **工作区 Notes**: 独立内容创作区，支持 AI 辅助编辑

### 应用到 Climber

- 模型选择器增加能力标签和状态指示
- 增加知识库 `#` 快捷引用机制
- 输入区域增加拖拽文件上传的视觉反馈

---

## 3. Dify

**仓库**: langgenius/dify | **Stars**: 151.3k | **技术栈**: Next.js, React Flow

### UI 设计特点

| 维度 | 特点 |
|------|------|
| 布局 | 工作流画布全屏 + 节点配置抽屉 |
| 配色 | 紫色渐变主色，节点类型色彩编码 |
| 交互 | 拖拽连线、节点实时预览、变量绑定 |

### 可复用模式

1. **工作流编辑器**: 基于 React Flow 的可视化 DAG 编辑器
2. **节点配置抽屉**: 右侧滑出面板，表单分组
3. **实时预览**: 节点级输入/输出预览
4. **应用模板**: 一键从模板创建应用

### 应用到 Climber

- 工作流编辑器优化节点连接视觉反馈
- 增加节点配置抽屉的分组表单
- 增加应用模板选择器（已有 WorkflowsPage，需增强）

---

## 4. ChatGPT-Next-Web (NextChat)

**仓库**: ChatGPTNextWeb/NextChat | **Stars**: 88.6k | **技术栈**: Next.js, TailwindCSS

### UI 设计特点

| 维度 | 特点 |
|------|------|
| 布局 | 极简双栏：会话列表 + 全宽聊天 |
| 配色 | 黑白为主，极简克制 |
| 交互 | 消息导出、Prompt 模板(Mask)、Artifacts |

### 可复用模式

1. **会话导出**: 支持 Markdown/JSON/截图/ShareGPT 导出
2. **Prompt 模板 (Mask)**: 预定义上下文模板，快速启动对话
3. **Artifacts**: 生成内容（代码/HTML）独立预览窗口
4. **自动压缩**: 长对话自动摘要压缩，显示压缩指示器

### 应用到 Climber

- 增加会话导出功能（Markdown/JSON）
- 增加 Prompt 模板系统
- Artifacts 独立预览面板（代码/SVG/HTML）

---

## 5. LibreChat

**仓库**: danny-avila/LibreChat | **Stars**: 41.6k | **技术栈**: React, TailwindCSS, Express

### UI 设计特点

| 维度 | 特点 |
|------|------|
| 布局 | ChatGPT 风格增强：侧栏 + 聊天 + 工具面板 |
| 配色 | 蓝紫色调，清晰的层级对比 |
| 交互 | 消息搜索、编辑重提交、会话分支、Resumable Streams |

### 可复用模式

1. **消息搜索**: 全局搜索所有对话消息，高亮匹配
2. **编辑重提交**: 任意消息可编辑并重新生成后续
3. **会话分支**: 从任意消息点分叉新对话
4. **Resumable Streams**: 断线自动恢复，多标签同步
5. **Reasoning UI**: Chain-of-Thought 动态展示面板

### 应用到 Climber

- 全局消息搜索（已有 GlobalSearch，需增强结果展示）
- 会话分支可视化
- Reasoning 过程展示面板（已有 ReasoningPage，需优化）

---

## 6. FastGPT

**仓库**: labring/FastGPT | **Stars**: 29.2k | **技术栈**: Next.js, React Flow, tRPC

### UI 设计特点

| 维度 | 特点 |
|------|------|
| 布局 | 工作台风格：左侧导航 + 中央画布 + 右侧配置 |
| 配色 | 蓝色主色调，清爽专业 |
| 交互 | 工作流调试模式、知识库测试、FAQ 管理 |

### 可复用模式

1. **工作流 Debug**: 逐步执行 + 节点日志实时查看
2. **知识库测试**: 单条查询测试面板，显示召回结果
3. **混合检索可视化**: BM25 + 向量 + 重排结果展示
4. **应用评测**: A/B 测试、ELO 排行榜

### 应用到 Climber

- 工作流增加 Debug 模式
- 知识库测试面板
- 节点执行日志实时展示

---

## 7. LineCode Pro

**仓库**: LangLang03/LineCodePro | **Stars**: 70 | **技术栈**: Java, Android Views

### UI 设计特点

| 维度 | 特点 |
|------|------|
| 布局 | 移动端单 Activity + Drawer 导航 |
| 配色 | Material Design 深色主题 |
| 交互 | Tool Call 卡片、Diff 历史、SSH 文件树 |

### 可复用模式

1. **Tool Call 卡片**: 工具调用结果渲染为独立卡片
2. **Diff 历史**: 文件变更时间线，支持回滚
3. **上下文压缩指示器**: 显示对话上下文使用率和压缩状态
4. **安全策略**: URL 白名单、路径保护、导出脱敏

### 应用到 Climber

- Tool Call 可视化卡片（已有基础，需增强样式）
- 文件 Diff 时间线视图
- 上下文使用率指示器

---

## 8. Continue

**仓库**: continuedev/continue | **Stars**: 35.3k | **技术栈**: TypeScript, VS Code Extension API

### UI 设计特点

| 维度 | 特点 |
|------|------|
| 布局 | IDE 内联：侧边栏对话 + 编辑器内联补全 |
| 配色 | 适配 VS Code 主题，跟随用户设置 |
| 交互 | Tab 补全、Inline Edit、多文件上下文 |

### 可复用模式

1. **Tab 补全**: 灰色 ghost text 预览，Tab 接受
2. **Inline Edit**: 选中文本后 AI 编辑，Diff 预览
3. **多文件上下文**: `@file` `@codebase` 语义引用
4. **Continue Panel**: 侧边栏对话，保持 IDE 上下文

### 应用到 Climber

- Monaco Editor 集成 Tab 补全 UI
- 增加 Inline Edit Diff 预览
- `@` 引用系统（文件/代码库/文档）

---

## 9. Cline

**仓库**: cline/cline | **Stars**: 65.6k | **技术栈**: TypeScript, VS Code Extension

### UI 设计特点

| 维度 | 特点 |
|------|------|
| 布局 | IDE 内嵌：聊天面板 + Diff 视图 + 终端 |
| 配色 | 绿色/琥珀色主调，清晰的执行状态 |
| 交互 | Plan/Act 模式切换、工具审批、Checkpoints |

### 可复用模式

1. **Plan/Act 模式**: 先规划后执行，用户确认计划
2. **工具审批流**: 每个工具调用需用户确认/拒绝
3. **Checkpoints**: 变更快照，支持一键回滚
4. **MCP 服务器管理**: UI 化管理 MCP 服务器连接
5. **多 Agent 编排**: 协调者-执行者模式可视化

### 应用到 Climber

- 自主执行页面增加 Plan/Act 模式切换
- 工具调用审批流程 UI
- Checkpoint 快照与回滚功能

---

## 10. Cursor

**仓库**: cursor/cursor (闭源) | **技术栈**: Electron, Monaco Editor

### UI 设计特点

| 维度 | 特点 |
|------|------|
| 布局 | IDE 布局：文件树 + 编辑器 + Cmd+K 面板 |
| 配色 | 暗色主题，渐变高亮 |
| 交互 | Composer 多文件编辑、Cmd+K 内联、Tab 预测 |

### 可复用模式

1. **Composer**: 同时编辑多个文件的 Agent 模式
2. **Cmd+K**: 内联 AI 编辑，选中即编辑
3. **Tab 预测**: 预测下一步编辑位置，Tab 跳转
4. **Agent 模式**: 自动理解项目结构，执行复杂任务

### 应用到 Climber

- Terminal/Editor 页面增加 AI 辅助编辑
- 文件树集成 AI 操作入口
- 多文件批量操作面板

---

## 设计模式汇总

### 布局模式

| 模式 | 适用场景 | 来源项目 |
|------|---------|---------|
| 三栏可调整面板 | 主工作区 | LobeChat, LibreChat |
| 全宽画布 + 抽屉 | 工作流编辑 | Dify, FastGPT |
| IDE 内嵌面板 | 代码辅助 | Continue, Cline, Cursor |
| 极简双栏 | 快速对话 | ChatGPT-Next-Web |
| 单 Activity + Drawer | 移动端 | LineCodePro |

### 交互模式

| 模式 | 描述 | 来源项目 |
|------|------|---------|
| Hover 操作栏 | 消息 hover 显示操作按钮 | LobeChat |
| @ 触发器 | @ 符号快速引用工具/文件 | LobeChat, Cursor |
| Plan/Act | 先规划后执行 | Cline |
| 审批流 | 每个操作需用户确认 | Cline |
| 会话分支 | 从任意点分叉 | LibreChat |
| Resumable Streams | 断线恢复 | LibreChat |
| Context Compaction | 长对话自动压缩 | LineCodePro |

### 组件库

| 组件 | 用途 | 来源项目 |
|------|------|---------|
| MessageBubble | 消息展示 | LobeChat, LibreChat |
| ToolCallCard | 工具调用结果 | Cline, LineCodePro |
| ModelSelector | 模型选择 | Open WebUI, LibreChat |
| WorkflowEditor | 工作流编辑 | Dify, FastGPT |
| DiffView | 代码差异 | Cline, LineCodePro |
| StreamingCursor | 流式指示器 | LobeChat, Open WebUI |
| KnowledgeBase | 知识库管理 | Open WebUI, FastGPT |
| PluginMarket | 插件市场 | LobeChat |

---

## 优先级实现清单

### P0 - 立即实现

1. **消息气泡增强**: 完善 hover 操作栏动画和布局
2. **模型选择器**: 增加能力标签和状态指示
3. **Tool Call 卡片**: 增强工具调用结果可视化
4. **流式指示器**: 增加上下文使用率显示

### P1 - 短期实现

5. **会话导出**: Markdown/JSON/截图导出
6. **Prompt 模板**: 预定义上下文模板系统
7. **工作流 Debug**: 逐步执行和节点日志
8. **Plan/Act 模式**: 自主执行页面模式切换

### P2 - 中期实现

9. **插件市场**: 卡片式布局和一键安装
10. **知识库管理**: 文档上传和检索测试
11. **消息搜索增强**: 搜索结果高亮和跳转
12. **Artifacts 预览**: 代码/HTML 独立预览窗口

### P3 - 长期实现

13. **会话分支**: 对话树可视化
14. **多 Agent 编排**: 协调者模式 UI
15. **IDE 集成**: Inline Edit 和 Tab 补全
16. **移动端适配**: 响应式布局优化

---

## 实现状态

### 已完成组件

| 组件 | 文件路径 | 状态 | 来源模式 |
|------|---------|------|---------|
| ModelSelector | `components/chat/ModelSelector.tsx` | 已完成 | Open WebUI, LibreChat |
| ContextUsageIndicator | `components/chat/ContextUsageIndicator.tsx` | 已完成 | ChatGPT-Next-Web, LineCodePro |
| PromptTemplates | `components/chat/PromptTemplates.tsx` | 已完成 | ChatGPT-Next-Web |
| StreamingStatus | `components/chat/StreamingStatus.tsx` | 已完成 | LibreChat, LobeChat |
| MentionPicker | `components/chat/MentionPicker.tsx` | 已完成 | LobeChat, Cursor |
| SessionExportMenu | `components/chat/SessionExportMenu.tsx` | 已完成 | ChatGPT-Next-Web |
| ExecutionModeToggle | `components/chat/ExecutionModeToggle.tsx` | 已完成 | Cline |

### 测试覆盖

| 测试文件 | 测试数 | 状态 |
|---------|-------|------|
| `ModelSelector.test.tsx` | 5 | 通过 |
| `ContextUsageIndicator.test.tsx` | 3 | 通过 |
| `ExecutionModeToggle.test.tsx` | 3 | 通过 |
| `SessionExportMenu.test.tsx` | 3 | 通过 |

### 导出入口

所有新组件通过 `components/chat/index.ts` 统一导出。
