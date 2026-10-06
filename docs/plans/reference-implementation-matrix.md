# 参考实施矩阵

核查日期：2026-10-02。范围：原索引 50 项与新增清单 32 个参考组，重叠 6 组，去重共 76 组；hermes-webui / ekko-studio 合并为一组、分别留证。仅阅读公开 README、源码和已有研究材料；未访问第三方 demo、安装或运行第三方 Agent，未修改应用代码，未 commit/push。

## 证据口径

- **S**：确认来源且有源码正文证据。覆盖的是列出的读取范围。
- **C**：新候选来源已读源码，名称或原地址对应关系仍待确认。
- **D**：README、书稿或配置证据；算法和产品实现仍待定点研读。
- **U**：来源未确认或公开访问失败。
- **复用**：来自 `ui-source-evidence.md`（UI）或 `backend-source-evidence.md`（BE）的既有实际阅读记录。旧记录缺少数字范围的文件保留原描述。
- 原索引补充表复用 `reference-coverage.md`（RC）及 `docs/references/deep-dives/` 下的核心（CORE）、世界模型（WORLD）、前端（FRONT）、记忆（MEM）与单项目报告；S 表示有记录的源码证据，版本缺失、文件级定位与当前主干迁移分别标注。旧报告的本地落地结论保留为历史映射，当前验证以本矩阵的本地核对表为准。
- 固定版本远程源码 URL 为 `https://raw.githubusercontent.com/{仓库}/{完整 SHA}/{文件路径}`；下表版本键对应版本表。本地源码行号取本轮工作区快照，可能随并发开发变化。
- 可移植项均为设计建议；当前实现、接线状态和真实运行验证分别列示。

## 全清单覆盖

| # | 用户参考 / 核实来源 | 状态 / 版本 | 实际阅读路径与范围 | 可移植设计 / Climber 映射 |
| --- | --- | --- | --- | --- |
| 1 | hermes-webui：`nesquena/hermes-webui`；ekko-studio：`EKKOLearnAI/ekko-studio` | S / HUI、EKKO | HUI `README.md` 1-120（前轮）；`api/state_sync.py` 前轮 1-160，本轮重试取得全文；EKKO 复用 UI：`packages/client/src/components/hermes/chat/ToolRunCard.vue` 1-32、`packages/client/src/composables/useToolTraceVisibility.ts` 1-35、`packages/client/src/components/hermes/skills/PendingWriteApprovals.vue` 1-100 | 明确会话/profile；usage 用累计绝对数；工具 id 聚合与审批提交态。映射 run_storage、工具卡、AnchoredPopupStack；HUI 的同步桥机制仍属建议 |
| 2 | `langchain-ai/agent-chat-ui` | S / CHAT | `README.md` 1-120（前轮）；`src/providers/Stream.tsx` 1-120；`src/components/thread/messages/tool-calls.tsx` 1-120 | thread 状态历史、独立 UI reducer、调用参数与结果分离、长结果折叠。映射 chatEvents/useChat；保留本地工具 id 更新契约 |
| 3 | `assistant-ui/assistant-ui` | S / AUI | `README.md` 1-120（前轮）；`packages/core/src/index.ts` 1-100；`packages/core/src/types/message.ts` 1-160、161-300；`packages/react/src/legacy-runtime/runtime-cores/external-store/ExternalStoreThreadRuntimeCore.ts` 1-5 | 消息 part 稳定 id、工具 interim/error/result 分离；审批 decision/select/text 类型与宿主授权语义；生成 UI 组件 allowlist。映射 chatEvents、弹窗栈；运行时重导出仅证明迁移边界 |
| 4 | `Tencent/WeKnora` | S / WK | 复用 UI：`frontend/src/views/chat/components/ToolApprovalCard.vue`、`ChatArtifactsPanel.vue` 各 1-100；`frontend/src/api/artifacts.ts` 1-100；`frontend/src/utils/traceAxis.ts` 1-84 | resolved/submitting 审批态；产物 session/message/index 标识；真实 duration 时间轴。映射审批栈、ArtifactPreview、TaskTracePanel；独立产物 API 待接通 |
| 5 | `labring/FastGPT` | S / FG | `README.md` 1-120（前轮）；`packages/service/core/workflow/dispatch/index.ts` 1-240、241-350、710-810、1300-1360 | v2 每 100ms 查停止标志，v1 查客户端中止；节点启动前停止检查；Set 去重与 maxConcurrency/Promise.race 调度；finally 清 timer、tracker、MCP 与停止记录。映射 workflow adapter、取消生命周期；运行中节点的内部中断传播仍待读 |
| 6 | `open-webui/open-webui` | S / OW | `README.md` 1-120（前轮）；`src/lib/components/chat/Messages/ResponseMessage.svelte` 1-120、670-715、810-970 | StatusHistory 受模型能力开关控制；ContentRenderer 接 content/output/sources 与 done；流式光标、独立 Error、Citations、CodeExecutions 分支；readOnly 限制保存/预览。映射消息卡与产物卡；子组件内部实现、密钥存储机制仍待补证 |
| 7 | `CopilotKit/CopilotKit` | S / COP | 复用 UI：`examples/showcases/a2a-travel/components/hitl/BudgetApprovalCard.tsx` 1-100；`examples/showcases/scene-creator/src/components/ArtifactPanel.tsx` 1-100 | 审批回调与已批准/拒绝展示分离；产物上下文编辑。映射审批栈、文件预览；完整 AG-UI 接入待验证 |
| 8 | openagent：候选 `openagentsinc/openagents` | C / OA | `README.md` 1-120（前轮）；`crates/ext-eval/src/lib.rs` 本轮全文（前轮 1-180 上限）；用户名称与复数仓库对应待确认 | subject/baseline 双臂，pure 评估与 runner 分离，grader door trait 可注入 fake。映射 evaluation runner；入口文档及导出支持模块边界，评分正文待读 |
| 9 | `langchain-ai/langgraph` | S / LG | 复用 BE：`libs/checkpoint/langgraph/checkpoint/base/__init__.py` saver 定义/存取协议；`libs/langgraph/langgraph/types.py` 215-229、460-523；`libs/langgraph/langgraph/pregel/_retry.py` 59-107 | checkpoint、attempt 身份、总时限/idle 时限。映射 run_storage 与 pregel；本地 workflow 的 pregel adapter 显式可选 |
| 10 | `microsoft/autogen` | S / AG | 复用 BE：`python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_base_group_chat.py` 680-746、748 起 save_state；`python/packages/autogen-ext/src/autogen_ext/experimental/task_centric_memory/memory_controller.py` 135-189 | 参与者 pause/resume 协议、执行 callback 与 grader 分离。映射 collaboration、evaluation；save_state 原记录未给结束行，保留边界 |
| 11 | `NousResearch/hermes-agent` | S / HA | 复用 BE：`agent/session_persistence.py` 1-3、34-60；`agent/retry_utils.py` 30、121；`tools/skill_manager_tool.py` 42、94/100、147、350；`plugins/memory/honcho/dialectic.py` 429 | transcript 去重、Retry-After/jitter、技能写入锁与 frontmatter 校验。映射 persistence、skills；Honcho 画像算法正文仍缺证 |
| 12 | `OpenHands/OpenHands`（旧 All-Hands-AI 地址重定向） | S / OH | 复用 UI：`src/types/agent-server/core/events/acp-tool-call-event.ts` 1-100；`src/stores/conversation-panel-preferences-store.ts` 1-100；复用 BE：`src/api/with-retry.ts` 4-25 | 工具终态、布局偏好、API 有界退避。映射 useChat、anchored store；当前版本为 Canvas，旧 Python controller 返回 404 |
| 13 | `TencentCloudBase/OpenAgentKernel` | S / OAK | 复用 BE：`src/public/create-agent.ts` 59-64、93-118；`src/permissions/drivers/in-memory-driver.ts` 18-55；`src/session-store/drivers/cloudbase-db-driver.ts` 146、335/365 | session/resume/HITL；project/conversation/toolUse 组合键。映射 run_storage、审批域；resumed 占位值保留为上游行为说明 |
| 14 | AgentScope：`agentscope-ai/agentscope`（旧 alibaba 地址重定向） | S / AS | 复用 BE：`src/agentscope/agent/_agent.py` 970、1135-1180；`src/agentscope/app/_service/_projectors/_subagent_hitl.py` 78、93、198；memory middleware 513-566、709 | unfinished 工具关闭、HITL parked、无进展检测、worker_session/reply 身份。映射 engine、collaboration；modelscope 别名沿用旧清单，当前 canonical 以 BE 核验为准 |
| 15 | `openai/openai-agents-python` | S / OAI | 复用 BE：`src/agents/memory/session.py` 53-91；`src/agents/run_state.py` 790-845；`src/agents/run_internal/session_persistence.py` 699、889、997、1104；`src/agents/retry.py` 117、143 | pending write 恢复、rewind、副作用重放独立授权。映射 run_storage、permission；run.py 原超时，前轮重试结果未核定，保持缺口 |
| 16 | CrewAI：`crewAIInc/crewAI`（旧 joaomdmoura 地址） | S / CR | 复用 BE：`lib/crewai/src/crewai/state/checkpoint_listener.py` 113、219、247；`memory/unified_memory.py` 76-110；`flow/human_feedback.py` 149、218、226、337 | checkpoint 事件、记忆权重、反馈蒸馏与存储。映射 collaboration、memory、进化门禁；收益需独立双集评估 |
| 17 | AgentGUI：旧 `AgentGUI-Team/AgentGUI` | U | API 404（UI）；前轮 `HEAD/README.md` 重试 404 | 保留来源缺口；待提供准确 owner/repo |
| 18 | `milisp/codexia` | S / CX | 复用 UI：`src/components/layout/AppLayout.tsx` 1-100；`src/bindings/ApplyPatchApprovalParams.ts` 1-22 | 布局 store 与类型化 patch 审批。映射 anchored layout/store；继续遵循本地三栏尺寸 |
| 19 | mastra-ui：旧 `mastra-ai/mastra-ui` | U | API 404（UI）；前轮 `HEAD/README.md` 重试 404 | 仓库归属与当前包路径待确认 |
| 20 | dyad-web：旧 `dyad-app/dyad-web` | U | API 404（UI）；前轮 `HEAD/README.md` 重试 404 | 仓库归属待确认 |
| 21 | agent-control-room：旧 `arkon-dev/agent-control-room` | U | 首次 API 403、重试 404（UI）；前轮 README 重试 404 | 名称待确认；保留访问状态 |
| 22 | json-render：`vercel-labs/json-render` | S / JR | `README.md` 1-120（前轮）；`packages/core/src/index.ts` 1-100、101-200；`packages/core/src/actions.ts` 1-160；`packages/react/src/renderer.tsx` 1-100 | component registry、event/action binding、confirm/onSuccess/onError、参数 schema。映射弹窗栈未来通用动作协议；执行行为仍需后半段源码证据 |
| 23 | agent-os：旧 `saadnvd1/agent-os` | U | 首次 API 403、重试 404（UI）；前轮 README 重试 404 | 名称冲突待消歧 |
| 24 | hermes-control-room：旧 `NousResearch/hermes-control-room` | U | API/raw 404；搜索候选 `CryptoDmitry/hermes-agent-control-room` 的 README 实为 Ghost Agent/Archon/Solana，内容冲突 | 候选内容冲突，继续保留来源缺口 |
| 25 | WorkDSH：候选 `techflag/workdsh`；旧 `WorkDSH/WorkDSH` | C / WD | 旧地址 API 404；候选 `README.md` 1-92；`workdsh-web/README.md` 1-120（前轮）；`docs/architecture.en.md` 1-23；`dsh-plugin-desktop/src/workdsh-main.ts` 1-160 | Profile 与桌面载体分离、明确资源版本、材料/任务/交付物关系。映射 workspace/artifact 设计；桌面入口证明载体实现，产品 UI 源码待读 |
| 26 | opencove：候选 `DeadWaveWave/opencove`；旧 `opencove/opencove` | D / OC | 旧地址 API/raw 404；候选 `README.md` 1-100；`package.json` 1-100 | README 描述工作空间恢复与状态可见性；配置确认 Electron/React 产品。映射布局偏好研究；画布恢复实现待读，来源对应待确认 |
| 27 | `bytedance/deer-flow` | S / DF | 复用 UI：`frontend/src/components/workspace/messages/tool-call-details.tsx` 1-100；`frontend/src/components/workspace/artifacts/context.tsx`、`artifact-viewer.tsx` 各 1-100 | 工具 input/result 分离、内嵌 details、会话域受控 artifact。映射工具卡、ArtifactPreview |
| 28 | agent-workspace：旧 `web3dev1337/agent-workspace` | U | API 404（UI）；前轮 README 重试 404 | 来源待确认 |
| 29 | cockpit：用户指定 `surething/cockpit` | U | 本轮 git ls-remote 凭证助手 500；官方 API `/repos/surething/cockpit` 与 raw `HEAD/README.md` 均 HTTP 404 | 来源地址已明确；公开请求未取得版本或正文。访问状态无法判定私有、迁移或不存在，保留源码缺口 |
| 30 | ai-agent-book：`bojieli/ai-agent-book` | D / 本地缓存无 SHA | 复用 `agi-book-gap-analysis.md`：`book/introduction.md`、`chapter1.md` 至 `chapter10.md`、`afterword.md` 共 12 文件/7476 行；前轮重读缓存 README | Model/Harness、评估五要素、双集门禁、四类更新载体、协作预算。映射 evaluation/metacognition；缓存无 git 元数据，既有分析含过时实施状态 |
| 31 | `bojieli/ai-infra-book` | D / INF | `README.md` 1-100；`manuscripts/11-资源调度与运行环境.md` 1-160；`calculations/calc.py` 1-11 | CPU 工作量与环境驻留分别度量；task/operation/attempt 各有标识；业务失败与执行故障分开。映射 run_storage/资源观测建议；calc.py 仅入口，计算实现待读 |
| 32 | `linshenkx/prompt-optimizer` | S / PO | 本地 clone remote/HEAD 核验；`packages/core/src/services/prompt/service.ts` 133-232 | 输入验证、模型选择、模板上下文、输出校验、历史由 UI 管理。映射本地 optimizer；本地采用原文证据与问题建议，原用户消息保持完整 |

## 原 50 项去重登记

原索引来自 `docs/references/open-source-projects.md`。重叠映射为原 #1→新增 #9、#2→#16、#4→#14、#9→#8、#12→#10、#25→#6。前五项沿用已有重定向/版本记录；AgentScope 原索引 modelscope 名称保留为历史别名。原 #9 明确指向 `openagentsinc/openagents`，其源码证据可归入确认来源；新增单数名称 `openagent` 的产品对应仍待确认。其余 44 项如下，候选仓库单列在同一参考组内，保留原地址失败状态。

| 原 # | 原项目 / 来源 | 状态 | 实际阅读证据 / 版本边界 | 设计映射 / 尚缺证据 |
| --- | --- | --- | --- | --- |
| 3 | `huggingface/smolagents` | D | CORE：README/元信息，范围与 SHA 未记录 | 工具注册；executor 正文待读 |
| 5 | `Significant-Gravitas/AutoGPT` | D | CORE：README/元信息，范围与 SHA 未记录 | 目标分解与复盘；循环正文待读 |
| 6 | `griptape-ai/griptape` | D | CORE：README/元信息，范围与 SHA 未记录 | 推理/工具/存储边界；实现待读 |
| 7 | `deepset-ai/haystack` | D | CORE：README/元信息，范围与 SHA 未记录 | pipeline 与失败策略；实现待读 |
| 8 | `PrefectHQ/prefect` | D | CORE：README/元信息，范围与 SHA 未记录 | 调度/阻塞；实现待读 |
| 10 | `microsoft/TaskWeaver` | D | CORE：README/元信息，范围与 SHA 未记录 | 代码执行前校验；实现待读 |
| 11 | `agno-agi/agno` | D | CORE：README/元信息，范围与 SHA 未记录 | 多工具执行；实现待读 |
| 13 | `ReasonWorld/reasonworld` | U | WORLD/RC：原地址 404 | 世界状态预测仅为设计方向 |
| 14 | `socratica/socratic-agents` | U | WORLD：原地址 404；RC 另记 socraticai 地址，二者分别保留 | 矛盾检测仅为设计方向 |
| 15 | `causal-ai/causalgraphgen` | U | WORLD/RC：原地址 404 | 因果图学习仅为设计方向 |
| 16 | `pymc-devs/pymc` | S | WORLD 文件级：`pymc/model/core.py`、`distributions/distribution.py`、`sampling/mcmc.py`、`sampling/forward.py`；SHA/行范围未记录 | 概率区间与校准；当前版本需重读 |
| 17 | `xorbitsai/symbolicai`；候选 `Xpitfire/symbolicai` | C | 原地址 404；WORLD 候选 `symai/symbol.py` Expression/__call__，文件级，版本未记录；另有 ExtensityAI 候选 | 符号契约；候选身份待确认 |
| 18 | `mini-world-ai/miniworld`；候选 `Farama-Foundation/Miniworld` | C | 原地址 404；WORLD 候选 `miniworld/miniworld.py`、`miniworld/envs/__init__.py`，文件级，版本未记录 | 环境观测/动作 benchmark；预测模型另需实现 |
| 19 | `yizhongw/self-consistency` | U | WORLD/RC：原地址 404；论文摘要证据单列 | 多答案一致性；实现无源码证据 |
| 20 | `thinkagent-ai/thinkagent` | U | WORLD/RC：原地址 404 | 反思回灌仅为设计方向 |
| 21 | `Inginnng/EditHere` | D | FRONT：README，范围/版本未记录 | 本地截图批注→结构化反馈；UI 正文待读 |
| 22 | `monkey-code-ai/monkeycode` | U | 原地址 404；FRONT 候选 lizepenggithub/monkeycode-ai-agent-worktrace README 一句话 | 思考流/补丁能力缺证，候选身份待确认 |
| 23 | `zcode-ai/zcode` | U | 原地址 404；FRONT 候选 zai-org/ZCode README，范围/版本未记录 | 桌面/Web/CLI 统一运行时方向；身份待确认 |
| 24 | `lobehub/lobe-chat` | S | RC：`src/features/AgentSetting/{SettingsModalLayout,AgentSettingsContent}.tsx`、`src/features/ChatInput/ActionBar/Params/{Controls,useParamsModelConfig}.tsx`、`src/layout/GlobalProvider/{AppTheme,NextThemeProvider}.tsx`、`src/store/global/initialState.ts`、`src/store/user/store.ts`、`src/app/layout.tsx`；LC，语义范围记录 | 模型能力驱动参数控件；README 当前称 LobeHub |
| 26 | `danny-avila/LibreChat` | S | RC：`client/src/components/Endpoints/EndpointSettings.tsx`，endpoint registry/preset 范围；LIB | 参数 registry；数字行范围缺失 |
| 27 | `langgenius/dify` | S | RC：`web/app/components/header/account-setting/model-provider-page/index.tsx`、`model-auth/add-custom-model.tsx`、`web/app/components/app/log/var-panel.tsx`，配置状态/Popover/变量折叠范围；DIFY | 多模型配置状态；数字行范围缺失 |
| 28 | `FlowiseAI/Flowise` | S | RC：`packages/observe/src/features/executions/components/` 下 ChatMessageBubble、ToolAccordionList、HitlPanel、ExecutionTreeSidebar；FLOW，语义范围记录 | 工具结果折叠/审批/任务树；FRONT 记录 README 归档提示 |
| 29 | `mckaywrigley/chatbot-ui` | S | RC：`components/models/model-select.tsx`、`components/sidebar/items/models/create-model.tsx`，模型搜索/创建字段范围；CB | 模型选择与校验；数字行范围缺失 |
| 30 | `vercel/chatbot` | D | FRONT：README；RC 本轮仅存在，范围/版本未记录 | 流式消息方向；正文待读 |
| 31 | `janhq/jan` | S | RC：`web-app/src/containers/dialogs/AddProviderDialog.tsx`、`web-app/src/containers/dynamicControllerSetting/index.tsx`，provider 校验/动态控件范围；JAN | 类型驱动设置；数字行范围缺失 |
| 32 | `bytedance/UI-TARS-desktop` | S | RC：`apps/ui-tars/src/main/agent/prompts.ts`、`apps/ui-tars/src/renderer/src/components/Settings/global.tsx`，提示词动作空间/设置 tabs 范围；TARS | 版本化提示词与设置分区；数字行范围缺失 |
| 33 | `letta-ai/letta`；另库 letta-code | S | MEM：`letta/schemas/memory.py` 68-79/143-173、`letta/orm/block.py` 36-50、`letta/orm/passage.py` 77-80、`letta/services/passage_manager.py` 396-436/543-560、`letta/functions/function_sets/base.py` 164-204/246-301/490-522；旧源码 SHA 缺失；letta-code `src/agent/memory-filesystem.ts` 29-35/92-121、`src/backend/local/initial-memory.ts` 55-56，版本缺失 | 历史内存工具与新版文件系统分开；RC 固定 LETTA 主干仅 README，不能给历史 Python 行号套此 SHA |
| 34 | `mem0ai/mem0` | S | MEM：`mem0/memory/main.py` 330-374/605-650/707-730/760-800/1642-1708/1747-1790、`mem0/utils/scoring.py` 16-40/60-139；版本缺失；RC 另读 `mem0/configs/{prompts,base}.py` 与 main.py，MEM0 | 身份域/混合排序；两批行范围与版本分别保留 |
| 35 | `run-llama/llama_index` | S | MEM：`llama-index-core/llama_index/core/base/base_retriever.py` 192-226、`query_engine/retriever_query_engine.py` 160-167/203-213、`indices/query/query_transform/prompts.py` 1-35、`indices/vector_store/base.py` 63-82；版本缺失 | retriever/postprocessor/query transform |
| 36 | `chroma-core/chroma` | S | MEM：`chromadb/api/client.py` 681-703、`api/segment.py` 956-1010、`segment/impl/metadata/sqlite.py` 113-225/524-590、`segment/impl/vector/local_persistent_hnsw.py` 428-470；版本缺失 | 元数据过滤与结果合并 |
| 37 | `qdrant/qdrant` | S | MEM：`lib/segment/src/types.rs` 3639-3660/4373-4410/4480-4520、`lib/collection/src/operations/types.rs` 490-543/676-696；版本缺失 | 布尔过滤与 payload 投影 |
| 38 | `11data/longmem`；候选 `Victorwz/LongMem` | C | 原地址 404；MEM 候选 `fairseq/fairseq/models/transformer_lm_sidenet.py` 254-308、`modules/sidenet_layer_palm_sidenet_retrieval.py` 192-208、`modules/joint_multihead_attention_sum.py` 132-188；版本缺失 | 检索增强 attention；原索引来源对应待确认 |
| 39 | `RecallWorks/Recall` | S | MEM：`src/recall/store.py` 24-31/47-48/60-75、`tools/remember.py` 31-53、`tools/recall.py` 26-49/96-105、`artifacts.py` 17-26；snapshot.py 仅文件级；版本缺失 | 类型化 Chroma 记忆与 Markdown 产物；图实现缺证 |
| 40 | `autoLearnMem/AutoMem` | S | MEM：`scaffolds/crafter_v5/agents/memory_agent.py` 747-824/2085-2185、`loop1_scaffold_evolution/meta_loop.py` 217-222、`loop2_training_engine/data_engine.py` 127-146；版本缺失 | LOG/PLAN 与训练数据；画像用途属于研究迁移 |
| 41 | `getzep/zep`；另库 graphiti | S | RC：`ontology/default_ontology.py` 本体定义，ZEP；graphiti-zep 报告仅文档，Graphiti 实现待读 | 示例本体与时序图引擎分开计证 |
| 42 | `evo-gpt/EvoGPT` | U | evogpt-404 报告：原地址 404 | 遗传算子无源码证据 |
| 43 | `beeevita/EvoPrompt` | S | evoprompt 报告：`run.py`、`evoluter.py`、`evaluator.py`、`utils.py`、`llm_client.py`；文件级，版本缺失 | population/evaluator/held-out 双集契约 |
| 44 | `PyEvolution/PyEvolution` | U | evogpt-404 报告：原地址 404 | 底层算子无源码证据 |
| 45 | `e2b-dev/E2B` | S | e2b 报告：`packages/js-sdk/src/sandbox/index.ts`、`packages/python-sdk/e2b/sandbox_sync/main.py`；另述 orchestrator/Firecracker/envd 文件级调用链，跨仓库归属与版本缺失 | 生命周期与隔离层级；runtime 版本需补证 |
| 46 | `opensandbox-group/OpenSandbox` | D | opensandbox 报告：README；RC 另记 alibaba 地址，重定向关系待补证 | 生命周期/出口/Vault 仅契约方向 |
| 47 | `guardrails-ai/guardrails` | S | guardrails-ai 报告 v0.11.0：`guardrails/guard.py` 86/384/485/834/872/884、`validator_base.py` 92/206/266/515/527/570、`run/runner.py` 143/168/205/350、`actions/reask.py` 19/33/43/450/584、`hub/install.py` 37；SHA 缺失 | 校验结果、动作与重问预算 |
| 48 | `facebookresearch/HyperAgents` | D | hyperagents 报告：README；明确源码未读 | 隔离评估循环方向 |
| 49 | `NVIDIA-NeMo/Guardrails` | D | nemo-guardrails 报告：README；RC 另记 NVIDIA/NeMo-Guardrails，地址关系待补证 | 五类 rails；注册/执行正文待读 |
| 50 | `protectai/rebuff` | S | rebuff 报告：`python-sdk/rebuff/detect_pi_heuristics.py`、`detect_pi_openai.py`、`detect_pi_vectorbase.py`、`sdk.py`；文件级，版本缺失 | 历史分层检测/canary 范式；归档项目保持参考用途 |

## 固定版本

| 键 | 仓库 | SHA |
| --- | --- | --- |
| HUI | nesquena/hermes-webui | `62e4d7b9e2560f9d49c0c29c2dc1414fbd4e2d12` |
| EKKO | EKKOLearnAI/ekko-studio | `ef9409601855557633edf07c08512b9dadb7a03f` |
| CHAT | langchain-ai/agent-chat-ui | `cf72cb0f68a04d24db93eb19afb2d46f3a5261d4` |
| AUI | assistant-ui/assistant-ui | `b6444661cf03cae6c5e10baba1e12c9e010b8ea0` |
| WK | Tencent/WeKnora | `bccb4b151bae403508da77fbb174efc79dc47c1a` |
| FG | labring/FastGPT | `c01b99ba549a44a7415ad2d660802b8211ace89f` |
| OW | open-webui/open-webui | `8bd8b4fac5e059578ac0c74b3c18d11139f88b7d` |
| COP | CopilotKit/CopilotKit | `f835ce816112541654ded07162c2cc8ddf4f3f2c` |
| OA | openagentsinc/openagents | `db7b1875937e9f5bdd05746fa42540ff7e3d30b8` |
| LG | langchain-ai/langgraph | `157a06dda988d85afeb8751ff27b35ab3f4f8bf4` |
| AG | microsoft/autogen | `027ecf0a379bcc1d09956d46d12d44a3ad9cee14` |
| HA | NousResearch/hermes-agent | `10c6188de188871f64a88dd95bc6b262adb0c307` |
| OH | OpenHands/OpenHands | `2414d6ee5e31bede2e78211f72b58e9949575a75` |
| OAK | TencentCloudBase/OpenAgentKernel | `959fa2ab007fa9a6ceb46bf42f5a09b765a841b9` |
| AS | agentscope-ai/agentscope | `72f3f6fa0b2fc38b8517f408ab616f0f2bd229e6` |
| OAI | openai/openai-agents-python | `a575a6e637feb9aea1b591237b007dd4991ddfba` |
| CR | crewAIInc/crewAI | `8078f9130c35a47be95d4a55bf1d73b3fd44fc88` |
| CX | milisp/codexia | `7e3cffee3534e2e242df8c20193c944ffc3cb7dd` |
| JR | vercel-labs/json-render | `fc2a696a50a30cb30c878ab1eb65e102487eea0f` |
| WD | techflag/workdsh | `4f2955bcacf07bafb9f72b59f9d412f2b74045e3` |
| OC | DeadWaveWave/opencove | `9126a04abf33845086b6ba4e1bd448c31af0a355` |
| DF | bytedance/deer-flow | `63e399f2bdf6ad1269724c10cfc98bb40c7550d3` |
| INF | bojieli/ai-infra-book | `3bdcb4fcab73010eeaccf31cc10a8242a895d82e` |
| PO | linshenkx/prompt-optimizer | `92c5aaadc43c60243a3ba68a2016183986e04d84` |
| LC | lobehub/lobe-chat | `e28847b36ecb287bd0ac72d51d1fee80408522ed` |
| LIB | danny-avila/LibreChat | `f10b1d91f1eee3a2c82d5247bf620351486b7c1b` |
| DIFY | langgenius/dify | `8055521b4923ce59ebebc4bd443c255a993cbdeb` |
| FLOW | FlowiseAI/Flowise | `9291856d1ea4a4ceea9f8fef8ce14f4f6c81e8eb` |
| CB | mckaywrigley/chatbot-ui | `81328b61d2a4ab597a7a057be70e785cf756d9f8` |
| JAN | janhq/jan | `14a720628f9592c8e60f7e081ef733076db8a6a9` |
| TARS | bytedance/UI-TARS-desktop | `2ff41a9e515828c5bd5b276e493d73aa0bdf4a3a` |
| LETTA | letta-ai/letta（当前文档主干） | `5bcdd177d70fa2b31a754cfcd801e77b2e1ab16a` |
| MEM0 | mem0ai/mem0（RC 批次） | `abb81c88e1f738a8117d8293530fbc31a5ef8fd9` |
| ZEP | getzep/zep | `495bf72880d13f0b81696ec4f88a9817ed85ca73` |

## Climber 当前映射

### Codex 桌面接线补充（2026-10-02）

- 用户已确认独立 Codex 桌面优先、常用模型与思考等级直接显示、运行中区分补充当前任务与排队下一任务。布局决策见 `frontend-anchored-ui.md` 最新优先级。
- 新读 Codex 固定版本：`openai/codex@a4bfd07d51fa941d70e41cc0345b631ab5a41224`。公开源码基地址：`https://raw.githubusercontent.com/openai/codex/a4bfd07d51fa941d70e41cc0345b631ab5a41224/`。
- 实际读取：`README.md` 产品入口；`codex-rs/app-server/README.md` 专题说明；`codex-rs/app-server-protocol/src/protocol/common.rs` 625–665、1933–1971；`protocol/v2/thread.rs` 62–162、354–435、913–1044、1394–1469、1680–1705、2058–2075；`protocol/v2/turn.rs` 1–200、280–470；`protocol/v2/project.rs` 1–196。
- 执行证据：`codex-rs/app-server/src/request_processors/turn_processor.rs` 1020–1167；`thread_queue_processor.rs` 1–349；`codex-rs/ext/queue/src/lib.rs` 1–22；`service.rs` 265–281、367–456、534–575；`codex-rs/core/src/codex_thread.rs` 402–441、548–577。上述省略目录的路径继承同一表项所在目录。
- 可借鉴契约：steer 绑定 threadId 与 expectedTurnId；独立持久队列使用稳定服务端 ID，启动成功后移除，队列变更后重新读取快照。协议证据与桌面 UI 视觉证据分别记录；本次未取得桌面组件源码。
- Hermes 新读：HA `website/docs/developer-guide/architecture.md` 1–160、`website/docs/integrations/providers.md` 1–160；HUI `ARCHITECTURE.md` 1–180、`static/messages.js` 1384–1505、`static/sessions.js` 2818–2846、8198–8270、9921–9990；EKKO README 名称迁移、Hermes/DSH 区分与许可证章节。README 长输出存在截断，保持全文待读边界。
- “DeepSeek Hermes”精确产品归属待确认：HA 支持 DeepSeek 供应商；EKKO 分别集成 Hermes 与 DSH。EKKO 为 BSL-1.1，本轮仅借鉴设计。
- 当前实施：锚定 Composer 已接入现有模型与思考等级控件；23 项定向测试通过。斜杠新增有界文字/错误反馈、取消与迟到回调隔离、目录键盘操作；26 项定向及51项相邻回归通过，typecheck 通过。测试使用 HTTP/SSE 桩；真实模型命令、完整命令工具事件接入与双队列尚待实施或验收。
- 新附件解析任务 `13928` 为33页，仍在 parsing；先前 `13927` 同样未返回正文。现有计划与参考矩阵用于推进已知需求，本次附件全文覆盖待解析结果确认。

以下为本轮只读核对；其余模块沿用旧证据，真实端到端效果仍需独立验证。

| 本地路径 / 读取范围 | 当前可确认行为 | 设计建议与验证边界 |
| --- | --- | --- |
| `frontend-react/src/types/chatEvents.ts` 1-138 | 归一化 event 行与 data.type；审批字段、工具结果、unknown 保留 | 覆盖现有本地事件名；完整 AG-UI 事件生态待验证 |
| `frontend-react/src/components/agent/AnchoredPopupStack.tsx` 1-168 | approval + toolCallId 才支持真实提交；成功后关闭，失败保留；params/confirm 的确认按钮禁用 | 扩展参数/确认交互需先定义后端响应契约；参考 assistant-ui 类型和 json-render actions |
| `frontend-react/src/components/anchored/TaskTracePanel.tsx` 1-197 | 账户任务快照 + 实时事件；epoch/sequence 合并；5 秒发现新任务；会话 trace 5 秒快照；群组任务树独立账户范围 | 旧 UI 证据的“仅轮询”已被当前工作区实现推进；会话关联、拖拽接口、真实订阅验证仍待补齐 |
| `frontend-react/src/components/anchored/ArtifactPreview.tsx` 1-42 | 成功文件工具输出、多文件受控选择、行变更标记、关闭 | 独立下载与版本管理契约待接通；Office 编辑能力属于新设计范围 |
| `app/core/engine/pregel/workflow.py` 1-200 | 保留 WorkflowEngine 节点语义；adapter 可选；max_attempts=1；失败返回 failed | FastGPT 入口/资源上下文可作设计参考；adapter 当前默认行为见文件说明 |
| `app/core/evaluation/runner.py` 1-200 | 注入 agent_fn/judge；失败轨迹强制不过；每候选新 session；token 预算；Principal 绑定；pass@k 与 Pass^k 估计区分 | Openagents 双臂机制可用于对照报告；真实数据集、真实模型收益待验证 |
| `app/core/prompt_optimizer/service.py` 1-103；`app/core/engine/runner.py` 1-150 | optimizer 接入新回合；原文 evidence 必须在原消息中；最多 3 问；单轮提示片段清理；异常仅记录类型 | 旧 optimizer 集成文档的“未实施”状态需按当前接线解释；优化收益待真实样本评估 |

## 异常与重试

| 请求 / 范围 | 原始结果 | 重试结果 / 影响 |
| --- | --- | --- |
| GitHub API repo/tree | `API rate limit exceeded for 103.156.242.197`；后续出口 `.194` 同类 403 | 改用限时 git ls-remote 取 HEAD 与固定 SHA raw；未声称取得新 tree |
| assistant-ui 旧路径 `packages/core/src/runtime-cores/external-store/ExternalStoreThreadRuntimeCore.ts`、`packages/core/src/runtime/external-store/external-store-thread-runtime-core.ts` | HTTP 404（前轮）；前一路径本轮另有 `TypeError: fetch failed` | React legacy 路径成功取得 1-5 重导出；core message.ts 成功，实际 runtime 实现待定位 |
| assistant-ui `packages/react/src/primitives/message/MessagePrimitiveParts.tsx`、`packages/react/src/primitives/composer/ComposerPrimitiveSend.tsx` | HTTP 404 | 通过 core 公共入口定位 message.ts，成功读取 1-300；React primitives 仍待定位 |
| json-render `packages/core/src/catalog.ts` | HTTP 404 | index.ts、actions.ts、renderer.tsx 成功；catalog 定义目录待定位 |
| HUI state_sync.py、OA ext-eval/lib.rs | 本轮 Node 请求 `TypeError: fetch failed` | curl 限时重试成功，取得全文；state_sync 首部“默认关闭”仅是模块说明，title/cwd 当前函数各有独立同步语义 |
| OpenCove package.json、ai-infra calculations/calc.py | `TypeError: fetch failed` | 第二批请求成功；calc.py 仅 CLI 入口，未研读计算算法 |
| Hermes Honcho / OpenAI run.py | 旧证据 HTTP 429 / read timeout | 前轮重试结果未核定；本矩阵继续列正文缺口 |
| ai-agent-book 缓存 git remote | `fatal: not a git repository (or any of the parent directories): .git` | 复用既有书稿阅读证据，版本标记为本地缓存无 SHA |
| AgentGUI、mastra-ui、dyad-web、agent-control-room、agent-os、hermes-control-room、agent-workspace 原地址 | 前轮 README 再试均 HTTP 404 | 逐项保留 U；公开访问失败仅说明该请求未取得正文 |
| surething/cockpit | git：`credential helper: server returned status 500`；`fatal: could not read Username for 'https://github.com/surething/cockpit.git': No such device or address` | 官方 API 与 raw HEAD README 重试均 HTTP 404；地址已明确，版本/正文未取得 |
| FastGPT dispatch 710-810、1300-1360 | Node 分别 `TypeError: fetch failed`、`TimeoutError: The operation was aborted due to timeout` | curl --max-time 22 限时重试取得正文，已逐段读取；241-350 与 open-webui 两批渲染范围均 HTTP 200 |

先前批量输出截断且未复核的文件请求均排除出成功计数。包括 HUI session_ops/chat.js、FastGPT ChatBox、Openagents coder lib、ai-infra 第 8 章等；可从固定版本继续定点读取。

## 完成度与优先缺口

- 清单登记：32/32 组（100%），全部有状态与处理说明。
- 确认来源且有源码正文：S 19/32（59.4%）。
- 候选来源已读源码：C 2/32（6.3%）；含候选共 21/32（65.6%）。
- 文档/配置层覆盖：D 3/32（9.4%）；ai-agent-book 为既有书稿阅读，ai-infra 为新章节局部阅读，OpenCove 为候选 README/配置。
- 来源未确认/失败：U 8/32（25%）。
- 原 50 项补充的 44 组：S 20、C 3、D 12、U 9，逐项登记 44/44。重叠原 #9 以原索引明确仓库计 S，新清单名称对应仍待确认。
- 去重登记：76/76（100%）；确认来源源码 S 40/76（52.6%）；候选源码 C 4/76（5.3%），含候选源码共 44/76（57.9%）；文档层 D 15/76（19.7%）；失败/未确认 U 17/76（22.4%）。这是混合新读与复用证据的覆盖统计，复用中的版本缺失仍列为缺口。
- 实施完成与真实验证：本次应用实施 0 项、应用运行验证 0 项。当前映射表登记 7 组只读本地行为，实施/接线/收益由对应任务独立验收；原索引的落地标记保留其历史语义。
- 以上比例按参考组计算；源码覆盖率表示至少一个定点源码证据。整仓研究完成度与 Climber 功能完成度需分别评估。

| 优先级 | 缺口 | 下一项具体研究 / 验收标准 |
| --- | --- | --- |
| P0 | 可见交互与真实提交范围 | 为 params/confirm 定义请求 id、payload、提交态、取消/超时和服务端确认；再定点读 assistant-ui runtime 与 json-render executeAction，验证成功后关闭、失败保留和幂等响应 |
| P0 | 恢复与副作用重放 | 补 OpenAI run.py、LangGraph saver 数字范围；核对本地 run_storage 的 pending write、attempt、取消恢复；使用离线契约测试，真实外部操作单独授权 |
| P0 | 评估证据与收益 | 读 Openagents grade/score/evaluate 正文；建立有来源的边界集与保留集、subject/baseline 同口径报告；记录真实执行与 fake 证据类型 |
| P1 | 工作空间/产物生命周期 | 定位 WorkDSH feature packages 与 OpenCove 恢复源码；确认候选来源；核对产物 session/message/version 标识与独立下载 API |
| P1 | FastGPT 调度与 open-webui 行为 | 已补 dispatch 停止/并发/清理与 ResponseMessage 模板分支；下一段读 workflowStatus/clientAbort 及 ContentRenderer/CodeExecutions 子组件，验证运行中取消传播和结构化产物处理 |
| P1 | 来源与版本缺口 | cockpit 地址已明确但公开请求失败；补其余 U 来源、4 组候选身份、旧记忆/沙箱源码 SHA，以及地址别名重定向证据 |
| P2 | 画像与资源量化 | 补 Hermes Honcho 正文、ai-infra 计算模块；以缓存命中、驻留内存时间、任务完成成本等真实观测评价设计 |

## 本次验证范围

本次仅更新本矩阵；核验两份清单数量、6 组重叠、76 组去重统计、固定 SHA 格式、表格结构与空白错误。应用测试、第三方运行、真实模型调用和浏览器验收均留待对应实施任务。既有工作区改动完整保留。
