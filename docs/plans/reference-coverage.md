# 参考项目覆盖表（50 开源仓库 + 20 系统提示词来源）

日期：2026-10-02。方法：`api.github.com/repos/OWNER/REPO` 取仓库元信息，配额受限期间改用 `git ls-remote`（git smart HTTP）取默认分支 HEAD SHA；再以 `raw.githubusercontent.com/OWNER/REPO/SHA/PATH` 定点读文件；404/结构核验用 github.com 页面状态码。未克隆整库、未访问在线演示站、未复制品牌资产。仅记录组件结构、交互范式与提示词架构的借鉴点。

前期研读记录见 `docs/plans/ui-source-evidence.md` 与 `docs/plans/backend-source-evidence.md`。本表"新读"指本轮定点读取了源码或提示词正文。

> 读状态权威性说明：记忆/前端/进化类某些仓库（如 mem0、llama_index、chroma、qdrant、Recall、AutoMem、EvoPrompt、E2B、guardrails、rebuff 等）本表标"存在-未读"，而 `reference-implementation-matrix.md` 对应行标 `S` 并记录了具体文件与数字行范围。两者不一致时，以矩阵行为准（其附有 file:line 证据）；矩阵无 SHA 的行仍需补 SHA 后才能算完全确证。本表"存在-未读"为更早一轮快照，未回填后续定点读取。

## 一、50 个开源参考项目

### A. Agent 后端内核（原清单 12 个）

| # | 仓库 | 本轮状态 | SHA | 关键借鉴点 | 建议落地位置 |
|---|---|---|---|---|---|
| 1 | langchain-ai/langgraph | 已读-前期 | `157a06dda988d85afeb8751ff27b35ab3f4f8bf4` | checkpoint 协议、TimeoutPolicy、attempt 身份 | app/core（engine 已对齐） |
| 2 | joaomdmoura/crewAI（现 crewAIInc/crewAI） | 已读-前期 | `8078f9130c35a47be95d4a55bf1d73b3fd44fc88` | checkpoint_listener、unified_memory 权重、human_feedback 蒸馏 | app/core |
| 3 | huggingface/smolagents | 存在-未读 | — | （轻量工具调用，本轮未安排定点研读） | — |
| 4 | modelscope/agentscope | 已读-前期 | `72f3f6fa0b2fc38b8517f408ab616f0f2bd229e6` | reasoning/acting 循环、HITL parked、busy loop 检测 | app/core |
| 5 | Significant-Gravitas/AutoGPT | 存在-未读 | — | — | — |
| 6 | griptape-ai/griptape | 存在-未读 | — | — | — |
| 7 | deepset-ai/haystack | 存在-未读 | — | — | — |
| 8 | PrefectHQ/prefect | 存在-未读 | — | — | — |
| 9 | openagentsinc/openagents | 已读-前期 | `db7b1875937e9f5bdd05746fa42540ff7e3d30b8` | （见 ui-source-evidence.md / backend-source-evidence.md 前期记录；SHA 以 reference-implementation-matrix.md 版本表 OA 行为准） | app/core |
| 10 | microsoft/TaskWeaver | 存在-未读 | — | — | — |
| 11 | agno-agi/agno | 存在-未读 | — | — | — |
| 12 | microsoft/autogen | 已读-前期 | `027ecf0a379bcc1d09956d46d12d44a3ad9cee14` | pause/resume RPC、save_state、task-centric memory | app/core |
| 补 | TencentCloudBase/OpenAgentKernel | 已读-前期 | `959fa2ab007fa9a6ceb46bf42f5a09b765a841b9` | session/resume/HITL 协议、组合键权限 driver | app/core |
| 补 | openai/openai-agents-python | 已读-前期 | `a575a6e637feb9aea1b591237b007dd4991ddfba` | pending write 恢复、rewind、副作用重试独立授权 | app/core |
| 补 | NousResearch/hermes-agent | 已读-前期 | `10c6188de188871f64a88dd95bc6b262adb0c307` | session_persistence、skill frontmatter 校验、jittered backoff | app/core |
| 补 | OpenHands/OpenHands（原 All-Hands-AI 重定向） | 已读-前期 | `2414d6ee5e31bede2e78211f72b58e9949575a75` | pause-event、with-retry 指数退避 | app/core |

### B. 世界模型/因果/元认知（原清单 8 个）

| # | 仓库 | 本轮状态 | SHA | 关键借鉴点 | 建议落地位置 |
|---|---|---|---|---|---|
| 13 | ReasonWorld/reasonworld | 404 | — | — | — |
| 14 | socraticai/socratic-agents | 404 | — | — | — |
| 15 | causal-ai/causalgraphgen | 404 | — | — | — |
| 16 | pymc-devs/pymc | 存在-未读 | — | （概率编程，本轮未安排定点研读） | — |
| 17 | xorbitsai/symbolicai | 404 | — | — | — |
| 18 | mini-world-ai/miniworld | 404 | — | — | — |
| 19 | yizhongw/self-consistency | 404 | — | — | — |
| 20 | thinkagent-ai/thinkagent | 404 | — | — | — |

### C. Agent 前端 UI（原清单 12 个）

| # | 仓库 | 本轮状态 | SHA | 关键借鉴点 | 建议落地位置 |
|---|---|---|---|---|---|
| 21 | Inginnng/EditHere | 存在-未读 | — | （重点对标仓库，本轮未列入定点研读名单） | — |
| 22 | monkey-code-ai/monkeycode | 404 | — | — | — |
| 23 | zcode-ai/zcode | 404 | — | — | — |
| 24 | lobehub/lobe-chat | 新读 | `e28847b36ecb287bd0ac72d51d1fee80408522ed`（默认分支 canary） | 详见下文"lobe-chat 细读记录" | 详见下文 |
| 25 | open-webui/open-webui | 已读-前期 | （见 ui-source-evidence.md） | 密钥本地存储、权限管理 | frontend-react |
| 26 | danny-avila/LibreChat | 新读 | `f10b1d91f1eee3a2c82d5247bf620351486b7c1b` | `client/src/components/Endpoints/EndpointSettings.tsx`：按 endpoint 从 settings registry 取 OptionComponent，preset/对话双模式复用；500px 滚动容器 | frontend-react/src/components/settings |
| 27 | langgenius/dify | 新读 | `8055521b4923ce59ebebc4bd443c255a993cbdeb` | `web/app/components/header/account-setting/model-provider-page/index.tsx`：系统级默认模型按模型类别逐槽位查询（textGeneration/embeddings/rerank/speech2text/tts）+ 配置状态机 no-provider/none-configured/partially-configured/fully-configured；`model-auth/add-custom-model.tsx`：受控/非受控 Popover + useAuth hook 双模式（configCustomModel / addCustomModelToModelList）；`web/app/components/app/log/var-panel.tsx`：变量折叠面板（{{label}} 徽标 + max-h 滚动） | frontend-react/src/components/settings |
| 28 | FlowiseAI/Flowise | 新读 | `9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb` | `packages/observe/src/features/executions/components/`：ChatMessageBubble（角色 chip + tool_call_id 徽章 + 内容抑制）、ToolAccordionList（available/called 双变体 + Used 徽章 + Show N more 分页）、HitlPanel（浮动 Proceed/Reject 条 + 反馈对话框 + 提交态）、ExecutionTreeSidebar（RichTreeView + 状态图标动画） | frontend-react/src/components（工具卡/任务树） |
| 29 | mckaywrigley/chatbot-ui | 新读 | `81328b61d2a4ab597a7a057be70e785cf756d9f8` | `components/models/model-select.tsx`：hosted/local tabs + 搜索 + 打开自动聚焦（注明 setTimeout hack）；`components/sidebar/items/models/create-model.tsx`：自定义模型五字段（name/model_id/api_key/base_url/context_length）+ "必须 OpenAI SDK 兼容"文案 | frontend-react/src/components/settings |
| 30 | vercel/chatbot | 存在-未读 | — | （AI SDK 基础件，本轮未安排定点研读） | — |
| 31 | janhq/jan | 新读 | `14a720628f9592c8e60f7e081ef733076db8a6a9` | `web-app/src/containers/dialogs/AddProviderDialog.tsx`：name/baseUrl/apiKey/apiType 四字段 + URL 正则校验 + 尾部斜杠清理 + 错误提示；`web-app/src/containers/dynamicControllerSetting/index.tsx`：controller_type 驱动五种控件（input/checkbox/dropdown/textarea/slider），Props 含 min/max/step/warnAbove/warnBelow/recommended（警告阈值与推荐值） | frontend-react/src/components/settings |
| 32 | bytedance/UI-TARS-desktop | 新读 | `2ff41a9e515828c5bd5b276e493d73aa0bdf4a3a` | `apps/ui-tars/src/main/agent/prompts.ts`：getSystemPrompt(language) zh/en 双语 + Thought/Action 输出格式 + 动作空间由 operator 生成（版本化 V1_5/Poki）；`apps/ui-tars/src/renderer/src/components/Settings/global.tsx`：Dialog+Tabs 设置分区（vlm/chat/localBrowser/report/general），zustand 开关 store | frontend-react/src/components/settings；提示词版本化→内置提示词版本管理 |
| 补 | bytedance/deer-flow | 已读-前期 | `63e399f2bdf6ad1269724c10cfc98bb40c7550d3` | 工具详情内嵌折叠 | frontend-react |
| 补 | EKKOLearnAI/ekko-studio | 已读-前期 | `ef9409601855557633edf07c08512b9dadb7a03f` | 工具卡受控展示 | frontend-react |
| 补 | CopilotKit/CopilotKit | 已读-前期 | `f835ce816112541654ded07162c2cc8ddf4f3f2c` | HITL 审批卡 | frontend-react |
| 补 | Tencent/WeKnora | 已读-前期 | `bccb4b151bae403508da77fbb174efc79dc47c1a` | 审批卡、trace 时轴 | frontend-react |
| 补 | milisp/codexia | 已读-前期 | `7e3cffee3534e2e242df8c20193c944ffc3cb7dd` | 布局 store | frontend-react |
| 补 | FastGPT（labring/FastGPT） | 已读-前期 | （见前期记录） | （见前期记录） | frontend-react |

### D. 记忆/用户画像（原清单 9 个）

| # | 仓库 | 本轮状态 | SHA | 关键借鉴点 | 建议落地位置 |
|---|---|---|---|---|---|
| 33 | letta-ai/letta | 新读-仅文档 | `5bcdd177d70fa2b31a754cfcd801e77b2e1ab16a` | 主干 README 声明源码已迁移至 letta-ai/letta-code；当前树仅文档与 .github（15 条目）。旧 MemGPT 内存管理提示词不在当前树中，未读到。letta-code 经 ls-remote 确认存在（`1fcc9666817ab852bc2532a3a989f712e1fd6c19`），本轮未深读 | app/memory（后续可去 letta-code 读） |
| 34 | mem0ai/mem0 | 新读 | `abb81c88e1f738a8117d8293530fbc31a5ef8fd9` | `mem0/configs/prompts.py`：FACT_RETRIEVAL_PROMPT 七类偏好分类 + few-shot JSON facts 输出 + "系统消息不提取"边界；`mem0/configs/base.py`：MemoryItem（id/memory/hash/metadata/score/created_at/updated_at）与 MemoryConfig（vector_store/llm/embedder/history_db_path/reranker/custom_instructions）分层；`mem0/memory/main.py`：BM25+实体加权混合召回、additive extraction、temporal/decay 用量通知 | app/memory（画像提取与记忆条目模型） |
| 35 | run-llama/llama_index | 存在-未读 | — | — | — |
| 36 | chroma-core/chroma | 存在-未读 | — | — | — |
| 37 | qdrant/qdrant | 存在-未读 | — | — | — |
| 38 | 11data/longmem | 404 | — | — | — |
| 39 | RecallWorks/Recall | 存在-未读 | — | — | — |
| 40 | autoLearnMem/AutoMem | 存在-未读 | — | — | — |
| 41 | getzep/zep | 新读 | `495bf72880d13f0b81696ec4f88a9817ed85ca73` | 仓库已转型为 Zep Cloud 示例/集成库（README 声明），开源时序知识图谱已迁至 getzep/graphiti。本轮读到 `ontology/default_ontology.py`：pydantic 本体定义（User/Assistant 单例实体、Preference 触发模式列表 "I want/like/prefer X..."、Location 分类优先级规则），是用户画像本体的直接范式 | app/memory（画像本体） |

### E. 自进化/沙箱/安全（原清单 9 个，编号 42-50）

| # | 仓库 | 本轮状态 | SHA | 关键借鉴点 | 建议落地位置 |
|---|---|---|---|---|---|
| 42 | evo-gpt/EvoGPT | 404 | — | — | — |
| 43 | beeevita/EvoPrompt | 存在-未读 | — | — | — |
| 44 | PyEvolution/PyEvolution | 404 | — | — | — |
| 45 | e2b-dev/E2B | 存在-未读 | — | — | — |
| 46 | alibaba/OpenSandbox | 存在-未读 | — | — | — |
| 47 | guardrails-ai/guardrails | 存在-未读 | — | — | — |
| 48 | facebookresearch/HyperAgents | 存在-未读 | — | — | — |
| 49 | NVIDIA/NeMo-Guardrails | 存在-未读 | — | — | — |
| 50 | protectai/rebuff | 存在-未读（设计文档注明归档） | — | — | — |

### lobe-chat 细读记录（SHA `e28847b36ecb287bd0ac72d51d1fee80408522ed`，默认分支 canary）

| 文件路径 | 读到 | 借鉴点 | 建议落地位置 |
|---|---|---|---|
| `src/features/AgentSetting/SettingsModalLayout.tsx` | header（avatar/title + 关闭）+ tabsBar（icon+label）+ 内容区三段式布局，antd-style createStaticStyles + cssVar token | 设置模态的标准骨架；cssVar 主题变量贯穿 | frontend-react/src/components/settings |
| `src/features/AgentSetting/AgentSettingsContent.tsx` | 按 ChatSettingsTabs 枚举渲染各 tab，serverConfig 特性开关 + 用户 lab 偏好双门控 | 设置项分级可见性（稳定特性直接开，实验特性走 lab 开关） | frontend-react/src/components/settings |
| `src/store/global/initialState.ts` | ChatSettingsTabs 枚举：Connector/Graph/Opening/Plugin/Prompt/SelfIteration；GroupSettingsTabs：Chat/Members/Settings | 设置 tab 的显式枚举契约 | frontend-react/src（settings tab 类型定义） |
| `src/features/ChatInput/ActionBar/Params/Controls.tsx` | 参数面板：temperature/top_p/presence_penalty/frequency_penalty 四参数，SliderConfig（max/min/step/unlimitedInput），i18n 键分 panel 标签与参数描述两层；`useParamsModelConfig` 按 model+provider 查询模型能力决定 disabledParams（模型不支持则禁用对应控件）；话题级模型覆盖 Agent 模型；usePermission 权限门控 | "模型能力驱动参数可用性"是自定义端点场景的关键交互：换模型时参数面板自动裁剪 | frontend-react/src/components/settings（模型参数面板） |
| `src/features/ChatInput/ActionBar/Params/useParamsModelConfig.ts` | hasModelConfig / disabledParams 选择器组合 | 参数禁用逻辑独立成 hook | frontend-react/src/hooks |
| `src/layout/GlobalProvider/AppTheme.tsx` | @lobehub/ui ConfigProvider + ThemeProvider，NeutralColors/PrimaryColors 双 token，FontLoader，useIsDark，cookie 同步 | 中性色与主色分离的主题 token 体系（iOS 化精致感的基础） | frontend-react/src/index.css（主题 token） |
| `src/layout/GlobalProvider/NextThemeProvider.tsx` | next-themes：disableTransitionOnChange + enableSystem + attribute="data-theme" + defaultTheme="system" | 暗色模式系统跟随的标准接法 | frontend-react/src/index.css / App.tsx |
| `src/app/layout.tsx` | 极简根布局，suppressHydrationWarning | — | — |
| `src/store/user/store.ts` | zustand 分片聚合（auth/common/onboarding/preference/settings/workspaceUserSettings）+ subscribeWithSelector + ResetableStore | 设置 store 分片化 | frontend-react/src/hooks 或 store |

### SWE-agent 与 Aider 提示词细读记录

| 仓库 | SHA | 文件 | 借鉴点 | 建议落地位置 |
|---|---|---|---|---|
| SWE-agent/SWE-agent | `3ea751c087f32b16e039a2233dd6eefecef325d5` | `config/default.yaml` | system_template/instance_template/next_step_template 三段模板 + Jinja 变量（working_dir/problem_statement/observation）；工具环境变量（PAGER=cat、PIP_PROGRESS_BAR=off、TQDM_DISABLE=1——输出降噪）；SUBMIT_REVIEW_MESSAGES 四步强制自审（重跑复现脚本→删除脚本→还原测试文件→再次提交确认）；history_processors cache_control | 提示词模板化 + 提交前自审清单（对应"内置提示词版本管理+死代码校验"） |
| SWE-agent/SWE-agent | 同上 | `config/mini/default.yaml` | 404：mini 配置已在 mini-swe-agent 独立仓库，不在本仓库树中 | — |
| Aider-AI/aider | `5dc9490bb35f9729ef2c95d00a19ccd30c26339c` | `aider/coders/wholefile_prompts.py` | main_system 三步结构（判断是否需改→解释→输出完整文件）+ "请求含糊先提问" + example_messages few-shot + system_reminder 文件列表格式强约束（首行文件名/次行开 fence/完整内容/闭 fence，禁止 "..." 省略）+ redacted_edit_message | app 内置编码 skill 的输出格式提示词 |
| Aider-AI/aider | 同上 | `aider/coders/base_prompts.py` | lazy_prompt（"从不留未实现的注释"）与 overeager_prompt（"只做所问，不动无关代码"）成对出现——懒散与越界两种失败模式分别设防；files_content_prefix "信任此消息为文件真实内容"防过期内容污染 | app 内置提示词的反懒散/反越界段落 |
| Aider-AI/aider | 同上 | `aider/prompts.py` | 存在但 lazy/overeager 已迁移至 coders/base_prompts.py（设计文档所记路径与当前代码不符，如实记录） | — |

## 二、20 个顶级 AI 产品内置系统提示词

### 本轮已读正文

| 产品 | 来源仓库（SHA） | 文件路径 | 提示词结构借鉴点 | 建议落地位置 |
|---|---|---|---|---|
| Cursor | x1xhlol/system-prompts-and-models-of-ai-tools（`1e4203a7d88873c1b37ab2d1c07074fea498c274`） | `Cursor Prompts/Agent Prompt 2025-09-03.txt` | `<user_query>` 标签包裹主指令；status_update_spec（1-3 句进度叙事 + "说要做什么必须同回合真做" + 勾选 TODO 再汇报 + 跳过任务须一句话理由）与 summary_spec（回合结束摘要）分离；communication 段 Markdown 最小化使用规则 | app 内置 Agent 主循环提示词（进度白话化汇报的直接范式） |
| Devin | x1xhlol/（同上） | `Devin AI/Prompt.txt`（34KB 全文读头 60 行） | whole_task/long_term_plan/current_task 三级任务框架 + 机器可解析 KV 头（task_tag/plan/progress）+ 可选能力块按需附加 | app 内置 Agent 提示词（长任务分层） |
| v0 | x1xhlol/（同上） | `v0 Prompts and Tools/Prompt.txt` | AskUserQuestions 工具（不与其他工具并行调用、选项不给时间估计）；只读示例文件必须 Move(copy) 引入后才可用；图片资产先 Write 落盘再以本地路径引用；console.log("[v0] ...") 调试约定与"解决后删除" | app 内置前端生成 skill 的提示词 |
| Manus | x1xhlol/（同上） | `Manus Agent Tools & Prompt/Prompt.txt` | 能力自述式系统提示词（从产品视角枚举工具面与边界） | app 内置通用 Agent 提示词 |
| Codex CLI (gpt-5.6-sol) | 0xeb/TheBigPromptLibrary（`cabcdb04b5970211b1b6163d8725ae66bb48c5f0`） | `SystemPrompts/OpenAI/20260902-Codex-CLI-gpt-5.6-sol.md` | 人格化段落（"与用户共享一个工作区"）+ "先结论后过程"技术交流规则 + 避免过度格式化（最小 Markdown） | app 内置编码 Agent 提示词（语气段） |
| Claude Code (Opus 5 interactive) | 0xeb/（同上） | `SystemPrompts/Anthropic/20260902-Claude-Code-Opus5-interactive.md` | `# Harness` 段（工具运行在权限模式后、被拒调用不原样重试、hooks 输出视作用户反馈、file_path:line_number 可点击引用、独立工具调用可并行） | app 内置 Agent 提示词（harness 段落结构） |
| GPT-5 | 0xeb/（同上） | `SystemPrompts/OpenAI/20251027-gpt5.md` | 工具禁用态显式声明（"bio tool is disabled"）；canvas 工具仅在 100% 确定用户意图时启用 | app 提示词的工具禁用/启用声明段 |
| Claude Code on the web (Fable 5.1) | asgeirtj/system_prompts_leaks（`b884b4a636e6c38e8266c1d56d98f47210dae16c`） | `Anthropic/claude-code/claude-code-cloud-fable-5.1.md` | 前置 `<reasoning_effort>` 档位数值映射表（low=10/medium=15/high=25/xhigh=80/max）+ thinking_mode auto | 思考等级（低/中/高）档位与模型 reasoning_effort 参数的直接实现依据 |
| Windsurf | x1xhlol/（同上） | `Windsurf/Prompt Wave 11.txt` | 目录核验存在，正文本轮未读 | — |
| 0xeb 库本体 | 0xeb/（同上） | `SystemPrompts/README.md`、`README.md` | provenance 头部范式：Contributed by / on / Source / Note / 字符数，verbatim 收录原则 | 内置提示词版本管理的元数据格式 |

### 本轮仅核验存在（未读正文）

| 来源仓库 | 状态 |
|---|---|
| gregkonush/claude-system-prompts | HTTP 200，未读正文 |
| agenticloops-ai/agentic-apps-internals | HTTP 200，未读正文 |
| EliFuzz/awesome-system-prompts | HTTP 200，未读正文 |
| caifyoca/CL4R1T4S | HTTP 200，未读正文 |
| Kilo-Org/kilocode | HTTP 200，未读正文 |
| timothygin/system-prompts-and-models-of-ai-tools | HTTP 200，未读正文 |
| yohan-work/agentive | HTTP 200，未读正文 |
| Sudhir1709/claude-code-system-prompts | HTTP 200，未读正文 |
| SWE-agent/mini-swe-agent | x1xhlol 树中无此仓库；mini-swe-agent 为独立仓库，本轮未核验 |

20 清单中：x1xhlol 目录已核验（Cursor/Devin/v0/Manus/Windsurf/Same.dev/Lovable/Perplexity/Trae/VSCode Agent/Augment Code/Replit 均在树中，另含 Kiro/Junie/Gemini/Emergent/dia/Comet Assistant/CodeBuddy/Cluely/Anthropic/Amp/Orchids.app/Poke/Qoder/Traycer AI/Warp.dev/Xcode/Z.ai Code/Leap.new）。NotionAI 条目指向 EliFuzz/awesome-system-prompts（存在）。

## 三、本地落地基准

- 前端：`frontend-react/src`（App.tsx、components、layout、hooks、api.ts、i18n；既有 anchored UI 五卡面板与任务/工具卡）。
- 后端：`app/`（api、core、memory、headless、integrations、models、middleware；核心调度在 `app/core/engine/`，含 tool_exec.py、sub_agent.py 等）。
- **本地无 `app/prompts` 目录**（本轮 `ls /workspace/climber/app` 核实：api/core/headless/integrations/memory/middleware/models/config.py/main.py）。表中"app/prompts"均指未来建立统一提示词目录时的建议位置，当前提示词逻辑内联在 `app/core/engine/` 与 `app/api/v1/`。
- 借鉴原则：不引入新依赖；UI 只借鉴结构与范式；提示词只借鉴段落结构与流程模板，不复制品牌或专有文案。

## 四、最值得落地的 5 个借鉴点

1. **模型能力驱动参数面板裁剪**（lobe-chat `src/features/ChatInput/ActionBar/Params/Controls.tsx` + `useParamsModelConfig.ts`）
   - 范式：参数面板固定四参数（temperature/top_p/presence_penalty/frequency_penalty），但每个控件按当前 model+provider 的能力查询结果决定禁用（disabledParams），话题级模型可覆盖 Agent 级模型。
   - 落地：`frontend-react/src/components/settings/`（模型参数面板）。Climber 支持任意自定义端点后，不同模型参数面必然不齐，此交互避免"填了不生效"的假 UI。

2. **动态设置控件注册表**（jan `web-app/src/containers/dynamicControllerSetting/index.tsx` + `AddProviderDialog.tsx`）
   - 范式：controller_type（input/checkbox/dropdown/textarea/slider）驱动的控件注册表，单控件 Props 携带 min/max/step/warnAbove/warnBelow/recommended（越界警告 + 推荐值）；供应商对话框四字段 + URL 正则校验 + 尾斜杠清理。
   - 落地：`frontend-react/src/components/settings/`（供应商/模型配置表单）。Climber 的模型配置面板（自定义端点、API key、切换模型）可直接套用此结构，参数警告阈值对 LLM 参数（超温警告）尤其有用。

3. **执行详情的可复用工具展示组件族**（Flowise observe `packages/observe/src/features/executions/components/`：ChatMessageBubble / ToolAccordionList / HitlPanel / ExecutionTreeSidebar）
   - 范式：角色 chip + tool_call_id 徽章 + usedTools 与 called 双列表（available 变体带 Used 徽章与 Show N more 分页）；HITL 浮动 Proceed/Reject 条与反馈对话框、提交态分离；树形执行侧栏带状态图标。
   - 落地：`frontend-react/src/components/`（工具调用卡与任务树卡片）。与既有 anchored UI 工具卡互补，补齐分页与 Used 徽章这类轻量信息层。

4. **提示词版本化 + provenance 元数据头 + 三段模板结构**（0xEB 库 provenance 头 + SWE-agent `config/default.yaml` + asgeirtj claude-code-cloud 的 reasoning_effort 档位表）
   - 范式：每版内置提示词带 Contributed by/Source/日期/字符数元数据；模板拆 system/instance/next_step 三段，Jinja 变量注入任务上下文；提交前强制自审四步（重跑脚本→删脚本→还原测试→重提交）；思考档位与模型 reasoning_effort 数值映射表。
   - 落地：新建 `app/prompts/`（或 `app/core/prompts/`）承载内置提示词版本管理；三档思考等级（低/中/高）按 asgeirtj 档位表映射为模型参数；SWE-agent 的 SUBMIT_REVIEW 自审清单可吸收进"任务完成度校验"。

5. **反懒散/反越界提示词成对设防 + 状态更新纪律**（Aider `aider/coders/base_prompts.py` lazy_prompt/overeager_prompt + Cursor `Agent Prompt 2025-09-03.txt` status_update_spec）
   - 范式：lazy_prompt 明令"不留未实现注释"，overeager_prompt 明令"只做所问、不动无关代码"——两种失败模式分别设防；Cursor 的 status_update_spec 要求 1-3 句白话进度 + "说要做什么必须同回合真做" + 跳过任务给一句话理由 + 回合末摘要。
   - 落地：`app/core/engine/` 内置 Agent 提示词段落（对应用户"AI 汇报必须大白话"与"禁止表面完成"两条核心诉求；与既有捷径解检测互补）。
