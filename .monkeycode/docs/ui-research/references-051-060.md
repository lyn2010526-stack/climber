# UI 资料核验：051–060

核验日期：2026-09-25。目标项目：Climber。范围：用户给定的 51–60 原名。

## 核验口径与结果

- 本文件为独立补充核验；既有 `references-021-060.md` 和其他文件保持原样。本次唯一写入为 apply_patch 新增本文件；未 commit/push、安装依赖、安装或运行第三方 Agent，也未启动任何远端项目。
- 10/10 项实际搜索并尝试打开官方文档或候选作者材料。按编号统计，52–60 共 **9/10 项成功直读正文**；51 的官方站打开仅返回标题/空正文，单列读取受阻。9 项含主框架及歧义候选的成功阅读，不能解释成 9 个独立开源 UI 已确认。
- 层级：S = 搜索索引线索；D = 直接打开官方/作者 README 或文档正文；C = 直接读到源码；L = 直接读到 LICENSE。搜索摘要、链接存在、目录名和截图占位均不升级为源码证据；没有运行验证或视觉测评。
- 搜索分批合并请求；每项保留实际查询词。官方指项目所属组织或作者的一手材料，个人候选不代表同名商业产品背书。
- 默认分支、站点及搜索缓存可能变化。本次未锁定 commit SHA；日期表示取证日期，历史文档/标签单独注明，避免把历史 UI 与当前分支混为一体。
- 许可证按已读范围记录：README 声明与完整许可文件分开注明；主体框架的许可不自动覆盖未确认 UI、商业产品、素材及数据。
- Climber 交互均为建议，本次未检查其应用源码或后端契约；保持桌面优先、沿用现有身份机制。暂停、续跑、审批、导出等动作须有真实接口与状态支持后才能呈现。

## 051 · AgentBuilder（百度前端）

- **原名**：AgentBuilder（百度前端）。
- **身份状态**：部分定位、开源前端身份未确认。官方搜索结果对应“文心智能体平台 AgentBuilder”；“百度前端”没有唯一仓库地址。AppBuilder/千帆 Agent 开发平台材料单独处理。
- **实际搜索**：`百度 AgentBuilder 前端 开源 GitHub`；`"AgentBuilder" 百度`；`site.agents.baidu.com "AgentBuilder"`；`site:agents.baidu.com/docs "工作流"`；`"AgentBuilder" "github.com" "百度"`。
- **实际 URL 与读取结果**：[官网](https://agents.baidu.com/)；[工作流创建智能体](https://agents.baidu.com/docs/develop/agent/workflow_creation/)；[智能体开发](https://agents.baidu.com/docs/develop/agent/zero_code_develop/)；[平台运营规范](https://agents.baidu.com/docs/operations/platform_norms/)。均尝试直接打开，正文为空；工作流页另用 webfetch 读取仍只有文档中心标题；追加 `/index.html` 也不可访问。
- **读取层级与证据**：S。[官网索引入口](https://agents.baidu.com/?from=4) 标题自称“文心智能体平台AgentBuilder”；“工作流创建智能体/如何开始”索引描述基础配置、画布编排、预览调试与发布；这些仅作搜索线索，未计为直接阅读成功。
- **边界补查**：另尝试打开 [AppBuilder 文档候选链接](https://ai.baidu.com/ai-doc/AppBuilder/Jlt4dqv3h)，本轮直读返回 Internal Error，未取得有效正文，排除出有效阅读计数。该产品路径也不足以证明 AgentBuilder 前端开源。官网索引另出现“8月31日”入口调整通知，缺少年份且页面直读失败，本次不推断当前可用性。
- **Climber 可采用交互（仅建议）**：将基础配置、流程编辑、试运行结果分区；发布前展示真实校验结果。该建议为研究者推导，待官方正文补证后再比较具体交互。
- **许可证**：未核验；未定位且读取到官方开源前端许可。

## 052 · Coze开源版

- **原名**：Coze开源版。
- **身份状态**：确认到 `coze-dev/coze-studio`，是包含前端的可视化 Agent 开发平台。商业版能力需另行区分。
- **实际搜索**：`Coze studio official github`。
- **实际 URL**：[官方 README 原文](https://raw.githubusercontent.com/coze-dev/coze-studio/main/README.md)。
- **读取层级与证据**：D；`What is Coze Studio?` 明示 Go 后端和 React + TypeScript 前端；`Feature list` 区分 Agent、应用、工作流和资源；`Using the open-source version` 描述拖拽节点画布，并提示部分商业功能的差异。
- **Climber 可采用交互（仅建议）**：把工作流、插件、知识库作为可选择资源；编辑画布旁显示配置与试运行结果；缺少模型配置时显示明确阻塞原因。
- **许可证**：Apache-2.0，已读 README 的 `License` 声明；未打开完整 `LICENSE-APACHE` 条款。
- **边界**：未查看页面组件源码及运行效果；文档中的商业版教程链接不代表社区版全部支持。

## 053 · MetaGPT Web UI

- **原名**：MetaGPT Web UI。
- **身份状态**：确认主框架 `FoundationAgents/MetaGPT`；独立官方开源 Web UI 仓库未唯一确认。主 README 链接的公开演示与 MGX 产品分别记录。
- **实际搜索**：`MetaGPT Web UI official GitHub`。
- **实际 URL**：[主仓库 README](https://raw.githubusercontent.com/FoundationAgents/MetaGPT/main/README.md)；尝试读取 [演示 app.py 页面](https://huggingface.co/spaces/deepwisdom/MetaGPT-SoftwareCompany/blob/main/app.py) 及 [raw app.py](https://huggingface.co/spaces/deepwisdom/MetaGPT-SoftwareCompany/raw/main/app.py)，后两者失败，raw 经 webfetch 返回 transport error。
- **读取层级与证据**：D（主框架）。标题为 `The Multi-Agent Framework`；`Software Company as Multi-Agent System` 描述角色分工和文档产物；`Usage` 给出 CLI/库用法；`QuickStart & Demo Video` 明确链接 deepwisdom 的 Space。新闻区把 MGX 单列为产品。
- **Climber 可采用交互（仅建议）**：任务视图按角色与阶段整理产物，并显示产物来源；这是从框架工作流推导的交互建议，未声称在其 Web UI 中观察到。
- **许可证**：主框架 README 明示 MIT 徽章；独立 Web UI、Space 演示源码和 MGX 的许可未核验。
- **边界**：Space 源码读取失败；无法据链接或框架开源推出 MGX 前端开源、演示仍可运行，或某一具体 UI 布局存在。

## 054 · ChatDev UI

- **原名**：ChatDev UI。
- **身份状态**：确认到 `OpenBMB/ChatDev` 的 Web Console。已读主分支名称为 ChatDev 2.0 / DevAll。
- **实际搜索**：`ChatDev UI official GitHub`。
- **实际 URL**：[README](https://raw.githubusercontent.com/OpenBMB/ChatDev/main/README.md)；[文档目录](https://raw.githubusercontent.com/OpenBMB/ChatDev/main/docs/user_guide/en/index.md)；[Web UI 指南](https://raw.githubusercontent.com/OpenBMB/ChatDev/main/docs/user_guide/en/web_ui_guide.md)；[LICENSE](https://raw.githubusercontent.com/OpenBMB/ChatDev/main/LICENSE)。
- **读取层级与证据**：D + L；README 明示 `frontend/` 为 Vue 3 Web Console，并记录 2026-01-07 发布 2.0、旧版转到 `chatdev1.0` 分支。Web UI 指南 `Launch View` 描述选择流程、上传附件、输入任务，节点状态为 pending/running/success/failed；同一输出面板呈现日志、上下文和产物；`human` 节点等待用户输入后继续。
- **Climber 可采用交互（仅建议）**：建立“节点状态 + 输出面板”联动；待用户输入单列状态并展示所需上下文；任务完成后提供绑定本次 session 的产物集合。
- **许可证**：Apache-2.0，已直接阅读主分支 LICENSE；素材、数据及历史版本未单独核验。
- **边界**：本条以 2.0 文档为证，旧版虚拟公司可视化不自动等同当前 Console；没有实测导出、人审或恢复。

## 055 · OpenDevin UI

- **原名**：OpenDevin UI。
- **身份状态**：OpenDevin 改名 OpenHands 的关系有直接官方证据；按同一项目历史沿革处理。当前所读 `OpenHands/OpenHands` README 标题为 Agent Canvas，须区分历史名、当前仓库前端与 SDK。
- **实际搜索**：`OpenDevin renamed OpenHands official announcement`。
- **实际 URL**：[官方历史文章](https://www.openhands.dev/blog/openhands-from-readme-to-open-source-movement)；[当前仓库 README](https://raw.githubusercontent.com/OpenHands/OpenHands/main/README.md)；[LICENSE](https://raw.githubusercontent.com/OpenHands/OpenHands/main/LICENSE)。补查 [frontend/README.md](https://raw.githubusercontent.com/OpenHands/OpenHands/main/frontend/README.md) 返回 404，未将该路径当作当前结构。
- **读取层级与证据**：D + L。官方文章日期为 2024-10-17，`Part 1: Answering the call` 中 Robert Brennan 直接称 `OpenDevin repo (before the rename to OpenHands)`；这是明确改名证据，文章日期仅为佐证发布日期。当前 README 的 `Repository boundaries` 把本仓库定位为 Agent Canvas 前端/控制中心，把 Agent Server 与运行事件归入 `software-agent-sdk`。
- **Climber 可采用交互（仅建议）**：工作区常驻显示执行后端及隔离方式；切换后端时明确影响的会话与资源范围；避免用户把本地执行和远端执行状态混淆。
- **许可证**：当前所读主分支 LICENSE 为 MIT；未追溯全部 OpenDevin 历史标签或其他 OpenHands 仓库许可。
- **边界**：只确认上述改名关系和当前读取内容；未推断精确改名日期、完整迁移版本链，未把商业云能力并入开源前端。

## 056 · SWE-agent UI

- **原名**：SWE-agent UI。
- **身份状态**：确认官方历史版 0.7 任务操作 Web UI，以及当前 `latest` 文档中的轨迹 Web Inspector；两者用途和版本分别记录，旧版 UI 的当前维护状态未确认。
- **实际搜索**：`SWE-agent UI web official documentation`；`site.swe-agent.com "web" "interface"`。
- **实际 URL**：[0.7 Web UI 文档](https://swe-agent.com/0.7/usage/web_ui/)；[当前 README](https://raw.githubusercontent.com/SWE-agent/SWE-agent/main/README.md)；[v0.7 LICENSE](https://raw.githubusercontent.com/SWE-agent/SWE-agent/v0.7/LICENSE)；[当前 CLI 文档](https://swe-agent.com/latest/usage/cli/)；[轨迹检查器文档](https://swe-agent.com/latest/usage/inspector/)。
- **读取层级与证据**：D + L；历史文档定位于单个 GitHub issue/本地仓库任务，声明仅涵盖部分 CLI 选项；手工启动段落明示 React 前端与 Flask 后端，分别使用 3000/8000 端口。当前 README 提示开发重心已转向 mini-swe-agent；当前检查器文档说明 `sweagent inspector` 可在浏览器查看 `.traj`，支持目录/端口参数，评测结果需匹配 `results.json`。
- **Climber 可采用交互（仅建议）**：任务创建区分 issue URL、仓库和问题描述；连接诊断分为页面服务、执行 API、运行环境；历史轨迹检查与新任务启动分设入口，缺少评测数据时显示未知状态。
- **许可证**：已读 v0.7 LICENSE，MIT；当前 README 也明示 MIT，历史 UI 的依据以 v0.7 为准。
- **边界**：当前官方文档明确标注 SWE-agent 整体处于 maintenance-only 模式；旧版操作 UI 的单独维护情况未确认。代码代理的 Agent-Computer Interface 与人类使用的 Web UI 分别处理；Codespaces 链接单独不足以证明当前提供同一图形界面。

## 057 · Browser Use UI

- **原名**：Browser Use UI。
- **身份状态**：确认到 `browser-use/web-ui`，与底层 `browser-use/browser-use` 库分开记录。
- **实际搜索**：`Browser Use web UI GitHub browser-use`。
- **实际 URL**：[README](https://raw.githubusercontent.com/browser-use/web-ui/main/README.md)；[启动入口 webui.py](https://raw.githubusercontent.com/browser-use/web-ui/main/webui.py)；[界面源码 interface.py](https://raw.githubusercontent.com/browser-use/web-ui/main/src/webui/interface.py)；[LICENSE](https://raw.githubusercontent.com/browser-use/web-ui/main/LICENSE)。
- **读取层级与证据**：D + C + L；README 明示 Gradio、保留浏览器会话、录屏与 VNC 观察入口。`webui.py` 调用 `create_ui`；`interface.py` 的 `create_ui` 实际创建 Agent Settings、Browser Settings、Run Agent、Agent Marketplace/Deep Research、Load & Save Config 标签页。
- **Climber 可采用交互（仅建议）**：把模型/Agent 配置、执行环境配置和本次运行分区；保留任务日志与浏览器观察入口的关联；复用浏览器会话需显示作用域及用户确认。
- **许可证**：MIT，已直接读取该 web-ui 仓库 LICENSE。
- **边界**：源码确认的是标签组织和调用连接；未读取各 tab 全部实现，也未验证录屏、浏览器控制或配置持久化的实际运行效果。

## 058 · Agent Reach UI

- **原名**：Agent Reach UI。
- **身份状态**：歧义；已读 `Panniantong/Agent-Reach` 和同名候选 `jgalea/agent-reach`。两者所读材料描述能力层/CLI，独立 Web UI 身份未确认。
- **实际搜索**：`"Agent Reach" UI GitHub`；`"Agent-Reach" Panniantong github`。
- **实际 URL**：[Panniantong 英文 README](https://raw.githubusercontent.com/Panniantong/Agent-Reach/main/docs/README_en.md)；[jgalea README](https://raw.githubusercontent.com/jgalea/agent-reach/main/README.md)。
- **读取层级与证据**：D（候选作者材料）；前者 `Design Philosophy` 定义职责为选取、安装、健康检查及路由，`Status at a Glance` 展示 doctor 命令的渠道状态；后者以 manifest 描述按需安装渠道，`Use` 提供 `doctor --json` 与 CLI 输出。
- **Climber 可采用交互（仅建议）**：将已有连接器呈现为能力健康表，显示实际后端、检查时间和错误原因；明确区分“凭据存在”与“真实调用通过”。这是从 CLI 诊断推导的界面建议。
- **许可证**：Panniantong README 的许可徽章明示 MIT；jgalea README 的 License 段明示 MIT；均未直接读取 LICENSE，且不能据此给未确认 UI 标注 MIT。
- **边界**：未安装、运行其安装器、Skill 或第三方工具；未把 README 中外链的浏览器产品当作本项目 UI。

## 059 · Multi-Agent Workbench

- **原名**：Multi-Agent Workbench。
- **身份状态**：泛称歧义，无法唯一定位。已读两个作者候选，保留各自身份与许可边界。
- **实际搜索**：`"Multi-Agent Workbench" github`；`"Multi-Agent Workbench" "neron82"`；`"Multi-Agent Workbench" "UBC-FRESH"`。
- **实际 URL**：[neron82/agent-workbench README](https://raw.githubusercontent.com/neron82/agent-workbench/main/README.md)；[UBC-FRESH/agent-workbench README](https://raw.githubusercontent.com/UBC-FRESH/agent-workbench/main/README.md)。
- **读取层级与证据**：D（候选作者材料）。neron82 候选自述 Web UI，`Features` 列出工作区/会话组织、可复用团队、Chat/Research/Work 类型、实时工具结果与停止操作；`Project structure` 指向 Flask/Jinja 模板。UBC-FRESH 候选自述监督式多 Agent 开发 sandbox，介绍工作契约、Python 包和 CLI。
- **Climber 可采用交互（仅建议）**：会话标注用途和工具预算；角色卡显示模型、职责、所属运行；聚合工具调用和结果。采用前核对 Climber 是否已有对应状态/预算字段。
- **许可证**：未确认。neron82 README 的 License 段仅写 `Internal project — Nous Research / Agent Workbench`，不足以确立具体开源许可；UBC-FRESH 未核验 LICENSE。公开可读与获得开源授权分别记录。
- **边界**：尚无证据证明用户原名唯一对应 neron82；UBC-FRESH CLI 与前者 Web UI 保持独立。没有安装或调用候选提及的 Hermes 等 Agent。

## 060 · AgentVerse UI

- **原名**：AgentVerse UI。
- **身份状态**：带同名歧义；确认到候选 `OpenBMB/AgentVerse` 框架内的本地仿真 GUI 示例，独立通用生产工作台未确认。检索另命中 `docs.agentverse.ai` 的同名 Dashboard 文档，不能仅凭原名将两者合并。
- **实际搜索**：`AgentVerse UI OpenBMB github`。
- **实际 URL**：[主 README](https://raw.githubusercontent.com/OpenBMB/AgentVerse/main/README.md)；[ui/README.md](https://raw.githubusercontent.com/OpenBMB/AgentVerse/main/ui/README.md)；[LICENSE](https://raw.githubusercontent.com/OpenBMB/AgentVerse/main/LICENSE)；[同名 Dashboard 文档候选](https://docs.agentverse.ai/v-1/documentation/blog/agentverse-ui)（搜索索引可见，直接打开返回 Internal Error，未计为正文阅读成功）。
- **读取层级与证据**：D + L；主 README 的 `Simulation / GUI Example` 明示 `agentverse-simulation-gui --task simulation/nlp_classroom_9players` 和本地 7860 网页，示例为一位教授、八位学生。`ui/README.md` 仅有 `Work in progress`。
- **Climber 可采用交互（仅建议）**：协作运行显示参与者、角色与所属场景，消息明确发言者；提供按角色过滤记录的入口，减少多 Agent 输出混读。
- **许可证**：主仓库 Apache-2.0，已读取 LICENSE；各示例素材与依赖需分别核验。
- **边界**：主 README 源文本中的 Pokemon / `cd ui` 说明处于 HTML 注释块，并标注历史 `release-0.1`；未当作当前受支持的通用 UI。任务求解 CLI 与仿真 GUI 的覆盖范围分别判断。

## 未确认项与优先建议

- **阅读缺口**：51 官网/文档正文无法直接取得，搜索索引仅作线索；53 Space 的 blob/raw 源码均未读到；55 猜测的 `frontend/README.md` 路径为 404。未收到明确 HTTP 403；各失败按真实返回记录，未伪写为 403。仓库主要证据均直接使用 raw URL。
- **身份缺口**：51 的百度开源前端仓库、53 的独立开源 UI、58 的 UI、59 的唯一指代待确认；56 已区分历史 0.7 操作 UI 与当前轨迹检查器；60 确认 OpenBMB 候选的仿真示例，同名 Dashboard 归属映射与开源 UI 身份待确认。55 的 OpenDevin → OpenHands 改名由官方文章直接确认。
- **建议 1：执行可观测性优先**。参考 54 的节点状态与输出联动，为每次运行绑定日志、上下文和产物；等待人类输入独立显示，动作以真实后端契约为前提。
- **建议 2：配置与运行分区**。参考 52、57，将 Agent 配置、资源/浏览器配置及本次执行结果分开；参数来源、配置缺口和试运行结果可见。
- **建议 3：环境与能力状态透明**。结合 55 的后端边界、56 的连接诊断和 58 的渠道检查，显示执行位置、隔离方式、依赖健康及最近验证结果；凭据存在不等于连接验证成功。
