# 22 项审查状态与范式采用

日期：2026-09-25。范围：project-wiki 局部 sync；本组仅新增本文件与 `ui-research/REFERENCE_INDEX.md`。应用源码、测试、既有报告和 MEMORY 保持只读；保留其他组修改；本组未 commit/push。

## 快照与证据边界

- 读取时 HEAD：`8cfca77abb7d79b7e0d3afe4a75e2e2532d7dd10`。工作树含已修改和未跟踪源码；此 SHA 仅标识比较基线，完整工作树快照仍待主会话锁定。
- 源码依据为定向读取及 `git diff --unified=1/2 -- <指定文件>`；文中函数、类型及测试名为定位锚点，路径相对项目根目录。并行修改可能改变行号和后续状态。
- 原始 22 项完整清单尚未取得。编号关联依据当前任务交接和明确带编号的测试；4/5、17/18 仅有组合测试范围，单项标题仍待核对。保留所有编号，缺少定义的条目登记为证据不足。
- 本轮未执行应用测试、构建、外部模型调用或 Docker 启动。测试文件、断言、mock 结果结构仅证明用例存在；运行结论须由主会话补入命令、输出、退出码和对应代码快照。历史 MEMORY 中的通过数字与本轮验收分开。
- 研究覆盖和身份去重见 `ui-research/REFERENCE_INDEX.md`。以下“范式采用”表示本地研究建议与当前实现的对应关系；实现来源、复制授权及框架引入均需各自证据。

## 状态定义

| 状态 | 本文含义 | 运行证据要求 |
| --- | --- | --- |
| 已修 | 有明确缺陷定义、可定位的修订及闭合的静态修复范围 | 另列运行状态；声明通过时须附实际日志 |
| 部分 | 有实现或修订证据，仍有编号定义、接线、并行收尾或验收缺口 | 明列剩余边界 |
| 既有正确 | 所核对的既有行为符合限定要求，未将其归功于新修复 | 静态结论限定到具体行为 |
| 待验证 | 定义可知，环境或运行证据尚未完成 | 保留验收占位 |
| 证据不足 | 原始定义、具体接口或足以作结论的材料缺失 | 补齐定义与证据后再更新 |

## 逐项状态

下表状态针对完整审查条目；局部静态修订和既有正确行为另在后文列出。当前没有整项运行验收通过声明。

| 编号 | 审查范围及关联确定性 | 状态 | 当前证据与限定结论 | 主会话待补 |
| --- | --- | --- | --- | --- |
| 01 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 02 | 工厂配置与执行状态；review2 测试明确关联 | 部分 | `app/api/v1/settings.py` 的 `CurrentPrincipal`、`validate_update`；`frontend-react/src/pages/FactoryModePage.tsx` 有配置错误、重试、取消及失败状态；后端与前端 review2 用例存在 | 配置到任务执行的完整契约；scripted 测试日志和真实模型验收分别登记 |
| 03 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 04 | 协作问题；review45 组合范围 | 部分 | `app/core/collaboration/handoff.py` 新增 `HandoffMessage`；组合测试见 `tests/core/test_collaboration_review45.py` | 原始第 4 项定义、单项证据归属及测试日志 |
| 05 | 协作问题；review45 组合范围 | 部分 | `app/core/collaboration/hierarchical.py` 使用实际 group members 规划；缺 manager/worker、空计划和验证失败显式抛错 | 原始第 5 项定义、与第 4 项的准确分工及测试日志 |
| 06 | 任务恢复；review6 测试明确关联 | 部分 | `app/core/recovery.py` 拒绝 pending writes 自动重放；恢复 checkpoint ID/终态；`auto_recover` 返回 recoverable 候选 | 恢复后实际继续执行、幂等与终态验收；发现候选和完成恢复分别记录 |
| 07 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 08 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 09 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 10 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 11 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 12 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 13 | 运行持久化；按交接由其他组实施 | 部分 | `app/core/engine/run_storage.py` 的 `RunStorage.begin` 关联 Session/Turn；`app/core/agent_engine.py` 引用存储层；`tests/isolated_engine_audit/test_runtime_persistence.py` 存在 | 并行组锁定最终实现；提交/异常/取消/重启读取与所有权隔离测试日志 |
| 14 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 15 | 外部服务客户端；交接明确 mock 边界 | 部分 | `tests/test_integration_clients_http_contract.py` 明确为本地 MockTransport 契约；Slack、Discord、Jira、Notion 客户端作为静态入口 | 本轮运行日志待补；真实凭据、真实服务调用及返回结果另行验收 |
| 16 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 17 | 安全/执行结果问题；17/18 组合范围 | 部分 | `tests/core/test_reported_security_regressions.py` 明确覆盖 17/18；`app/core/security/docker_sandbox.py` 已改用接口层 `ExecutionResult`/`ExecutionStatus` | 原始单项定义及证据归属；本地回归日志；真实 Docker 单独验收 |
| 18 | 安全链问题；17/18 组合范围 | 部分 | `app/core/engine/safety.py` 既有 mode、overlay、schema、sandbox 检查；差异扩展命令工具集合；`ExistingSafetyChainTests` 为用例证据 | 原始单项定义及证据归属；权限/工具/HTTP 边界的限定回归日志 |
| 19 | 接口问题；具体接口尚未给出 | 证据不足 | 已见任务路由身份及 owner 过滤修订；该局部证据不能定义第 19 项的全部接口范围 | HTTP 方法、路径、请求/响应、复现条件和预期行为 |
| 20 | Docker 构建与启动 | 待验证 | `Dockerfile` 有 web/api 分阶段差异；交接说明当前环境无 Docker；构建和容器启动均未验收 | 在具备 Docker 的验收环境提供镜像构建、启动、健康检查与日志；配置值脱敏 |
| 21 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |
| 22 | 原始定义待提供 | 证据不足 | 当前材料不足以绑定具体缺陷 | 原始描述、涉及文件、验收条件 |

整项状态合计：部分 8、待验证 1、证据不足 13；共 22 项。已修和既有正确仅用于下列有边界的局部判断。

## 局部静态判断

| 对象 | 状态 | 证据锚点及结论边界 |
| --- | --- | --- |
| Docker 返回值契约修订 | 已修 | `app/core/security/docker_sandbox.py` 差异由旧 stdout/returncode 构造改为 `app.core.interfaces` 的 status/output/metrics；缺容器、非零退出、异常和不可用分支均有显式结果。仅限所读返回值契约，真实容器待验证 |
| 层级协作错误传播 | 已修 | `app/core/collaboration/hierarchical.py` 的 `run_hierarchical_process`、`_plan_subtasks`、`_validate_output` 对缺成员、空计划及验证异常改为抛错；完整调用链与调度状态待验证 |
| 既有权限检查顺序 | 既有正确 | `app/core/engine/safety.py` 的 `validate_tool_call` 已有 mode、permission overlay、参数 schema、sandbox 检查顺序；本次局部 diff 仅扩展 `COMMAND_TOOLS`。该结论限定于已读检查链，所有工具覆盖仍待验收 |
| 恢复状态表达 | 部分 | `app/core/recovery.py` 的 `auto_recover` 发现可恢复候选；继续执行、工具重放及重启闭环需单独证据 |
| 模型发现 | 部分 | `app/api/v1/model_discovery.py` 按 credential ID、owner、active 状态读取并服务端解密；响应 no-store；`ModelSelector.tsx` 区分 loading/error/empty。并行组仍需确认路由和全部调用点接线 |

## 范式采用

研究编号属于百项参考索引，与 22 项审查编号分开。以下为交互建议与源码的对照；A/B/C 的具体色值、图标及样式属于 Climber 本地决策。

| 主题 | 研究依据或采用边界 | 当前源码与实际 diff | 结论及待验 |
| --- | --- | --- | --- |
| A 配色 | 采用低噪声、状态语义明确的本地设计方向；研究 099 建议颜色配合文字/图标；未指定外部项目原样配色 | `frontend-react/src/index.css` accent 由紫蓝调整为 slate 色系；新增明暗主题 foreground；图表使用 token | 已见 token 修订；全页面覆盖、对比度和明暗主题截图待验证 |
| B 图标 | 研究 099 的状态语义建议；语义图标使用现有组件体系 | `frontend-react/src/navigation/navConfig.ts` 将 Factory、Brain、Stethoscope、GitBranch 分别用于工厂、推理、诊断、追踪 | 导航差异已见；全站图标统一性待验证，其他页面仍需独立检查 |
| C 去特效 | 采用本地克制视觉方向；保持必要状态反馈 | `frontend-react/src/index.css` 移除 glow token/动画及多处渐变；`components/chat/EmptyState.tsx` 调整为 surface/border；`components/ui/ThemeToggle.tsx` 移除缩放旋转，保留颜色/透明度过渡（组件路径均相对 frontend-react/src） | 限定路径已见差异；全站特效清理和实际视觉效果待验证 |
| 工厂状态 | 研究 045 的规划/执行状态、流转及心跳范式；见 `ui-research/references-041-050.md`；研究 055/056/058 的环境与能力状态透明建议见 `ui-research/references-051-060.md` | `frontend-react/src/pages/FactoryModePage.tsx` 中配置 loading/error、task_retry、task_failed、取消与完成分支；`app/api/v1/settings.py` 使用身份和更新校验 | 当前配置、后端执行状态和真实调用结果需分层展示；第 02 项保留部分 |
| 模型发现 | 研究 058 的能力健康表建议及 066/067 的连接状态分离可作类比；实现归并行组 | `app/api/v1/model_discovery.py`、`app/services/model_discovery.py`、`frontend-react/src/components/chat/ModelSelector.tsx`；接口及选择器当前含未跟踪文件，应以全文核对补充 git diff | 凭据、模型列表、选择与错误状态已有静态入口；真实供应商和调用点接线待验证 |
| 凭据分离 | 研究 042 的 MCP 配置边界与 058 的凭据存在/调用通过区分；见对应九份报告条目 | `frontend-react/src/pages/ApiKeysPage.tsx` 命名模型凭据，移除复制/回显入口；`pages/AuthApiKeysPage.tsx` 命名平台访问令牌，使用统一 API；`lib/api-client.ts` 统一平台鉴权头与 `/api/v1`（后两路径相对 frontend-react/src） | 已见职责与入口分离；完整服务端权限、数据传输及回归待验证 |

上述采用均为交互范式对应。本组没有复制外部源码、图标或品牌资产，没有引入框架，也没有安装或运行第三方 Agent。

## 运行证据占位

下表全部待主会话填写。原始输出应脱敏并绑定最终工作树/提交；分别记录 collected、passed、failed、skipped，保留退出码。

| 范围 | 已知测试入口或验收目标 | 实际命令 | 时间与快照 | 输出路径及退出码 | 当前结果 |
| --- | --- | --- | --- | --- | --- |
| 02 工厂 | `app/api/v1/test_factory_configuration_review2.py`；`frontend-react/src/pages/__tests__/FactoryModePage.review2.test.tsx` | 待填写 | 待填写 | 待填写 | 未运行；scripted 与真实模型分开 |
| 04/05 协作 | `tests/core/test_collaboration_review45.py` | 待填写 | 待填写 | 待填写 | 未运行 |
| 06 恢复 | `tests/isolated/test_review6_task_recovery.py` | 待填写 | 待填写 | 待填写 | 未运行 |
| 13 持久化 | `tests/isolated_engine_audit/test_runtime_persistence.py` | 待填写 | 待填写 | 待填写 | 并行组补最终日志 |
| 15 外部服务 | `tests/test_integration_clients_http_contract.py` | 待填写 | 待填写 | 待填写 | 未运行；用例限定 mock |
| 17/18 安全回归 | `tests/core/test_reported_security_regressions.py` | 待填写 | 待填写 | 待填写 | 未运行；用例注明 no network or Docker |
| 模型发现 | `tests/test_model_discovery.py`；`frontend-react/src/components/chat/ModelSelector.test.tsx` | 待填写 | 待填写 | 待填写 | 并行组补接线、单测与真实供应商证据 |
| 19 接口 | 具体接口与契约待提供 | 待填写 | 待填写 | 待填写 | 证据不足 |
| 20 Docker | 构建、启动、健康检查与容器日志 | 待填写 | 待填写 | 待填写 | 当前环境无 Docker；未验收 |
| A/B/C 与凭据页面 | 类型检查、构建、定向前端测试及桌面/移动兼容截图 | 待填写 | 待填写 | 待填写 | 未运行 |

## 主会话更新顺序

1. 补入原始 22 项描述，确认 4/5 与 17/18 的准确映射；为第 19 项补充具体接口契约。
2. 等待 13 持久化及模型发现并行组收尾，核对实际入口/调用点，锁定完整代码快照。
3. 汇入与快照一致的测试原始日志；标清 mock、scripted、真实供应商和真实 Docker 的证据层级。
4. 逐项据证更新状态，保留未完成验收；核实研究身份歧义及未确认项的 owner/URL。
