# Agent 系统提示词开源仓库索引

> 来源：`docs/DESIGN.md`「完整资料汇总」部分的全量录入。
> 用途：为 `app/core/prompts/registry.py` 的提示词体系提供外部结构参考。
> 原则（同 `docs/prompt-system/README.md`）：只提炼结构与规范，不复制提示词文本。

## 一、Agent 核心角色与执行流程

| 项目 | 地址 | 提炼要点 | Climber 对应 |
| --- | --- | --- | --- |
| OpenHands | https://github.com/All-Hands-AI/OpenHands | Agent 作为"助手"的角色定义：彻底、有条理、质量优先 | core.system 角色段 |
| SWE-agent | https://github.com/SWE-agent/SWE-agent | Thought → Bash Command 响应格式；五步任务流程（查找→复现→修复→确认→边界）；提交前自我审查 | task.type=implementation 执行段 |
| Claude Code (Agent) | https://github.com/Sudhir1709/claude-code-system-prompts | APEI 协议（分析→计划→执行→迭代）；"理解先于行动，计划先于编辑" | core.system 工作流段 |
| REPOMIND | https://github.com/SRKRZ23/repomind | 全仓库上下文设计，精确引用文件路径与行号 | 工具契约（路径引用规范） |
| Devstral (OpenHands) | https://huggingface.co/unsloth/Devstral-Small-2507 | 效率、文件系统、代码质量、版本控制完整规范 | core.system 质量段 |
| Aider (Wholefile) | https://github.com/Aider-AI/aider/blob/main/aider/coders/wholefile_prompts.py | 确定修改→解释原因→输出完整文件 | task.type=implementation 输出格式 |
| Aider (Base) | https://github.com/Aider-AI/aider/blob/main/aider/prompts.py | lazy_prompt 杜绝只写注释；overeager_prompt 控制修改范围 | core.system 验证/约束段 |
| mini-swe-agent | https://github.com/SWE-agent/mini-swe-agent | 响应必须含一个 Bash 代码块，命令用 && / \|\| 连接 | 模型适配（格式约束） |
| Shamik/Versatile_Agent | https://github.com/Shamik-07/compound_ai_agentic_system | Thought → Code → Observation 循环，print() 输出关键信息 | 工具循环范式 |
| Claude Code (Subagent) | https://github.com/Sudhir1709/claude-code-system-prompts | 子 Agent："只要还有工作，就继续调用工具" | 子任务并发（task_worker） |
| oh-my-pi (Subagent) | https://github.com/can1357/oh-my-pi | 同上：还有工作时始终继续调用工具 | 同上 |
| Baltor/Loop Engine | https://github.com/alisonjieli-png/loop-engine | 每步任务启动新 Agent，避免长会话上下文腐烂 | 上下文压缩/会话恢复 |
| meow-dsh-workflow | （可能已改名/转私有，需搜索） | Agent 角色编译成系统提示词 + 工具白名单，多层语言链 | 工具白名单（permission_rules） |

## 二、顶级 AI 产品内置提示词（20 个）

### 编码与开发类

| # | 产品 | 地址 | 提炼要点 |
| --- | --- | --- | --- |
| 1 | Cursor | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Cursor%20Prompts | 仓库级 rules、持久指令分层 |
| 2 | Claude Code | https://github.com/gregkonush/claude-system-prompts | 主提示词 + 语气风格 + 限制规则 + 工具策略 |
| 3 | Devin AI | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Devin%20AI/Prompt.txt | "真实软件工程师"角色 + 工作流 |
| 4 | Replit Agent | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Replit%20Agent/Prompt.md | 专家自主程序员，特定环境构建 |
| 5 | v0 (Vercel) | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/v0%20Prompts%20and%20Tools/v0.MD | 组件化 UI 生成、设计还原 |
| 6 | Windsurf Agent | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Windsurf%20Agent | 代码导航、项目上下文理解 |
| 7 | GitHub Copilot | https://github.com/agenticloops-ai/agentic-apps-internals/blob/main/github-copilot/plan-mode/system-prompt.md | plan-mode 提示词、内容政策 |

### 通用与多能力类

| # | 产品 | 地址 | 提炼要点 |
| --- | --- | --- | --- |
| 8 | Manus | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Manus%20Agent%20Tools%20%26%20Prompt/agent%20loop.md | agent loop：规划、持久任务状态、进度导向执行 |
| 9 | Same.dev | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Same.dev | 系统提示词与内部工具定义同源开源 |
| 10 | Lovable | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Lovable | UI/UX 设计建议 + 代码生成 |
| 11 | Perplexity | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Perplexity | 信息检索、引用来源、答案合成 |
| 12 | NotionAI | https://github.com/EliFuzz/awesome-system-prompts | 提示词与笔记/文档/数据库深度绑定 |

### 模型基础与安全指令

| # | 产品 | 地址 | 提炼要点 |
| --- | --- | --- | --- |
| 13 | OpenAI GPT-5 Thinking | https://github.com/EliFuzz/awesome-system-prompts | 深度推理、分步思考指令 |
| 14 | Anthropic Claude | https://github.com/gregkonush/claude-system-prompts | 安全准则、帮助性定义 |
| 15 | Google Gemini | https://github.com/EliFuzz/awesome-system-prompts | 多模态理解、结构化输出 |
| 16 | xAI Grok | https://github.com/caifyoca/CL4R1T4S | 个性化系统提示 |
| 17 | Kilo Code | https://github.com/Kilo-Org/kilocode | 模式特定行为 + 工具化编码工作流（已对齐） |
| 18 | Augment Code | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Augment%20Code | 代码上下文注入、精确补全 |
| 19 | VSCode Agent | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/VSCode%20Agent | 与 IDE 环境/编辑器 API 深度交互 |
| 20 | Trae AI | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Trae | 中文开发者本地化优化 |

## 三、大型聚合库

| 库 | 地址 | 规模 | 用途 |
| --- | --- | --- | --- |
| timothygin/system-prompts | https://github.com/timothygin/system-prompts-and-models-of-ai-tools | 30+ 工具 | 一站式对照 |
| TheBigPromptLibrary | https://github.com/0xeb/TheBigPromptLibrary | 1851 条 / 25+ 提供商，含中文 | 跨厂商结构对比 |
| system_prompts_leaks | https://github.com/asgeirtj/system_prompts_leaks | 40k+ Star | 新产品提示词追踪 |
| agentive | https://github.com/yohan-work/agentive | 100 个 Agent 提示词 + 运行手册 + 评估方法 | 提示词评估方法论 |
| Claude Code v2.1.19 (Piebald) | https://github.com/Sudhir1709/claude-code-system-prompts | 全部提示词 + 18 内置工具描述 | 工具描述规范 |

## 四、补充仓库

### 提示词工程

- awesome-chatgpt-prompts: https://github.com/f/awesome-chatgpt-prompts
- Prompt-Engineering-Guide: https://github.com/dair-ai/Prompt-Engineering-Guide
- huggingface/prompt-hub: https://github.com/huggingface/prompt-hub
- system-prompts-collection: https://github.com/kyegomez/system-prompts
- agent-system-prompts: https://github.com/AgentOps/agent-system-prompts

### Skill / 工具仓库

- modelcontextprotocol/servers: https://github.com/modelcontextprotocol/servers （MCP 生态）
- agentops/agent-skills: https://github.com/agentops/agent-skills
- openai/plugins: https://github.com/openai/plugins
- BerriAI/litellm: https://github.com/BerriAI/litellm （多模型网关）
- langchain-ai/langchain-tools: https://github.com/langchain-ai/langchain-tools
