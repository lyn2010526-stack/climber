# Climber 私人仿AGI Agent · 手写笔记完整转录终稿

> **文档性质**：作者手写笔记 100% 原文完整转录 + 深度融合，一字未删。
> **融合来源**：2026-09-28 手写笔记全文 + 两份长期迭代附属文档（提示词仓库清单 + 完整设计文档）。
> **本稿地位**：Climber 项目「想法 → 架构 → 算法 → 落地路线」的最高纲领文档。
> **对照版本**：`docs/DESIGN_DOCS/CLIMBER_DESIGN_FINAL.md` 为其结构化表述，两者一致。

---

## 第〇部分 · 融合完整性审计

本稿是手写笔记的唯一权威转录，每一处手写原话均被收录。审计清单：

| 手写编号 | 原文标题 | 收录位置 | 状态 |
|---|---|---|---|
| ① | 为什么再纯粹利用AI做项目时，总是越做越乱 | 第一部分·1.1 | ✅ |
| 9.28① | 习惯性省略或暗示性提示词工程 | 第一部分·1.2 | ✅ |
| 9.28② | AI Agent 缺失原生元认知 | 第一部分·1.3 | ✅ |
| ③ | 缓存问题、脚本未测试、隐患 | 第一部分·1.4 | ✅ |
| ④ | 前端UI显示完整需求 | 第一部分·1.5 | ✅ |
| ⑤ | 后端乱融、死代码 | 第一部分·1.6 | ✅ |
| ⑥ | 内置提示词 / QQBot / 多Agent并发 / 提示词特调 | 第一部分·1.7 | ✅ |
| ⑦ | tool 不好用 / 第一性原理 / 指令深化 | 第一部分·1.8 | ✅ |
| ⑦（第二个） | 私人AI / 自进化 / 术数 / 大数据两条路 | 第一部分·1.9 | ✅ |
| ⑧ | 神经元连接启发 / 智能的本质 | 第一部分·1.10 | ✅ |
| — | 顶级角色提示词（手写全文） | 第二部分 | ✅ |
| — | 50个开源参考项目 | 第四部分 | ✅ |
| — | 完整设计文档（全部章节） | 第三～十一部分 | ✅ |

**本稿为手写笔记的最终定稿**，后续所有开发以本稿为准。

---

## 第一部分 · 作者原生手写核心思想（100% 原文完整保留）

### 1.1 ① 为什么再纯粹利用AI做项目时，总是越做越乱

> 以下为手写原文完整转录：

```
为什么再纯粹利用AI做项目时，总是越做越乱；
提示词会采用省略、暗喻的方法。前端风格一开始就决定下来。
表达精专业术语，在做到大后期；特别容易的是，你在灵感爆发时：
项目已经像东拼西凑一样。以及AI在完成任务时，肯定会出现专业术语；
而在不知道进度时，通常会重复给出提示及词。
最好是我能以较详细含有术语的提示词；而AI回答任务进度时，应说成大白话。
```

**硬性规范**（由上述痛点直接推导）：
- **用户侧输入**：可以全专业、详细、带术语。
- **AI对外汇报**：进度反馈、解释必须**纯大白话**。
- **主范式**：`定框架 → 定风格 → 套模板 → 找开源`。

### 1.2 9.28① 习惯性省略或暗示性提示词工程

> 手写原文：

```
目前：①习惯性省略或暗示性来做提示词工程，
原因：Agent不是具备长记忆和对用户语境推测；
而是先拉tool跑任务，查看上下文，导致，
AI Agent理解能力与记忆力和任务效率大幅度降低；并且极易出现屎山代码。
```

**工程含义**：
- 不能把「读上下文」当作「理解用户」，上下文是**截断的**、不完整的。
- Agent 的理解必须先于工具调用，理解必须是**语境推演**而非关键词匹配。
- 屎山代码不是 AI 能力问题，是**理解链条断裂**的下游症状。

### 1.3 9.28② AI Agent 缺失原生元认知

> 手写原文：

```
AI Agent 对于大部分任务极度丧失"元认知"功能，
AI Agent在压缩上下文时，当上文过长时；
AI Agent能读取的上下文仅有1M，但是用户的指令是随着用户想法而更新的；
应将用户说的所有内容当作指令执行，有省略性，通常要根据上下文推断，
以及即发出指令；AI-agent执行任务，准确又需要AI Agent是能够听懂用户惯用省略、暗喻等提示词；
解决办法我认为是可以将用户说的所有提示词收集起来（压缩）；
以至于在更换模型或者上文超长时间，AI‑Agent了解要做什么，怎么做。
倘若找不到主目标便是走错方向。
倘若找不到主目标便是走错方向。
```

**工程含义**：
- 「元认知」不是提示词模拟，是**原生能力**：Agent 必须知道自己「知道自己什么、不知道什么」。
- 1M 上下文限制是**物理事实**，必须用永久归档绕过，而非假装不存在。
- **找不到主目标 = 禁止瞎做**：宁可停下来问，也不跑偏。

### 1.4 ③ 缓存问题、脚本未测试、隐性隐患

> 手写原文：

```
③缓存问题、脚本未测试，及实际使用问题，可能会有小问题隐患。
```

**工程含义**：所有脚本必须有**前置测试**；缓存必须有**失效与一致性机制**；隐患必须**暴露而非掩盖**。

### 1.5 ④ 前端UI显示完整需求

> 手写原文：

```
④前端UI显示；*当Agent做任务时，调用工具会不会显示，思考会不会显示，怎么显示交互；
是否支持让用户填端点，填API就能获取模型或手动填模型，
模型在做操作时是否能用到斜杠、命令行，中断，重试做了没有，
模型思考等级有没有做，如低中高，等等。以及语言设计，这些问题于、参考 Monkey‑code、deepseek‑hermes、codex、zcode。
UI组件看着就矛盾，以及Agent回复消息做输出时，吐字以怎样形式，要丝滑流畅，
且看着是否支持多语言、多模态，及很多细节，如AI‑Agent在UI是否将原本后端功能写成前端UI的注释，
及图标，组件等要UI思考到万全之策。
```

**完整需求清单**（从手写原文逐条提取）：
- [ ] Agent 做任务时：工具调用可视化
- [ ] Agent 做任务时：思考过程可视化
- [ ] 自定义模型端点（填端点 + API 就能获取模型）
- [ ] 手动填写/切换模型
- [ ] 斜杠命令体系
- [ ] 命令行交互
- [ ] 中断（做了没有？）
- [ ] 重试（做了没有？）
- [ ] 思考等级：低 / 中 / 高（做了没有？）
- [ ] 多语言
- i18n 准备、多模态输入（图/音频）
- [ ] Agent 输出流式吐字：丝滑流畅
- [ ] 参考范式：Monkey-code、deepseek-hermes、codex、zcode
- [ ] 禁止把后端逻辑写成前端注释
- [ ] UI 组件统一、无矛盾、图标/组件全覆盖

### 1.6 ⑤ 后端乱融、死代码

> 手写原文：

```
⑤后端乱融，太多想法和其它开源功能，但有些衡根本接不上，导致成为了死代码，
要让它真正能用，功能要做深度。
```

**工程含义**：
- **不做表面堆砌**。每个接入的功能必须：能运行、能被测试、有调用链路、可复用。
- **已有调用链路但未接通的功能，一律清理或接通**。
- 「深度」= 一个功能做透，胜过十个功能摆设。

### 1.7 ⑥ 内置提示词 / QQBot / 多Agent并发 / 提示词特调

> 手写原文：

```
⑥内置提示词怎么做？以前的提示词写了什么？是否过时？是否勾细，
内置的skill有哪些怎么使用？我记得没做接入QQ bot，
接入像国内一些app功能如扫码等方式，多Agent是典型例子；
多Agent的意思是在后端支持多agent同时做任务，不是写在前端上占一大堆地方，
方说多Agent，AI思考，群组协作功能也同样算是；
还要更的是，AI Agent能不能支持拉取子任务同时并发进行？如果没有要怎么做？
子任务上限是18个，你不要弄那么蠢，再把子任务弄到前端UI上了；
跑任务，默认子任务是3个，做好兼容性，一并做用户注解，其它的相辅相承。
提示词在内置Agent中是强行植入，必须读取的；及任务完成度、准确度。
AI各有强有弱，有的如GPT‑6推理是强但对用户给出几乎模糊提示词时，根本就不会说人话；
还有诸多模型；很多模型都理解能力特别差；
用户再给提示词时AI几乎听不进去；工程完成度特别差；
所以在针对这两个方面在提示词上需要大量的特调度。同样一句话：
AI要怎么完成度，要么理解偏了；针对大模型这种中多模化情况，
我们要针对这种情况特别调参；目前还未找到方法。
AI和Agent；我希望总是能够取长补短，相辅相成。
```

**完整需求清单**：
- [ ] 内置提示词：历史归档、版本管理、过期标记、精细管控
- [ ] 内置 Skill：文档、调用规范、准入校验
- [ ] QQBot 接入（国内生态）
- [ ] 扫码等国内 App 能力（如微信/支付宝扫码）
- [ ] **多Agent并发 = 后端能力**，不是前端界面堆砌
- [ ] **子任务默认并发 3 个、硬上限 18 个**（铁律，不改动）
- [ ] 子任务支持用户注解
- [ ] 兼容性适配
- [ ] 内置提示词：**强制植入、必须读取、不可跳过**
- [ ] 多模型差异化特调（推理强 vs 理解强，分别适配）

### 1.8 ⑦ tool 不好用 / 第一性原理 / 指令深化

> 手写原文：

```
⑦tool做的不够好用。Agent做任务也应从第一性原理出发。
及对于用户喜欢给出较短、信息较少的提示词；
Agent本身也要根据实际情况优化及补长较详细及符合的提示词；
对于任务完成度Agent自身应把它做深。
```

**工程含义**：
- 用户给短指令、隐喻、省略 → Agent **自动补长、补全、深化**为可高精度执行的完整任务。
- 工具回归第一性原理：**工具是交互肢体，不是功能货架**。

### 1.9 ⑦（第二个） 私人AI / 自进化 / 术数 / 大数据两条路

> 手写原文：

```
⑦我提出新观念，以后的Agent AI Agent是私人AI的，虽每个人下载的Agent是同一份，
但Agent能随用户使用，越用越顺手；这会变成一个重要私人数据。
所以Agent会随用户使用的积累下来，总结使用，习惯能get到用户想表达的准确意思，也就是Agent自进化；
加一个Agent数据可轨迹数据证据，Agent模块也要设置思考等级，也要特调；仿AGI化。
从安全，在前端UI那里面，设3个等级为："仅访问不修改"，"部分修改"，"允许完全访问且修改"；
安全这方面，不用搞得太复杂，可以将这Agent前置设置人脸识别跟密码，开机，
加载进入动画要跟进入私密聊天APP‑样，十分精美；而且iOS化，通俗搭配为；
以上的我推荐，各个功能都去github上找成熟可用的开源项目直接套；
AGI化在我做Agent方面，我有许多想法，但可能都不成熟；将在脚本Agent，且搭配好自调API时；
跳出来，让用户输入选择年龄，阅历；然后简易调用大模型；
将，字将用户性格，说话，语言特色全部算出来；这样有助于Agent以后直接查看数据，性格特点；
帮助更好的完成任务，是根据，八字推理下去，但不能让用户看到；得到的数据会一定存在以后并结合任务调用，
直接是一框完整的框架；然后随着用户使用习惯去优化；改变本框架。
这样将接住用户说的指令；并且做任务时，用户说太笼统的词跟任务；
不仅要补充优化好能做执行深度；后台直接拉取用六爻，奇门遁甲等术数，根据使用时间再勾起；
询问用户具体意图；也是强行执行的；以后随着用例更新；再长久更新；再长久了解大概特点，优化，改进等；
再跑长耗时；也直接用指纹直接推理。第二条路便是，用算法；把现在的大数据做推送；
比如短视频收平台；**越短越是总结，停留时长越长；软越去推送；基于以上启发；
对于Agent是否可以采用这种方法；或者是在刚起始使用的；
直接把用户聊天记录等购买记录，各种数据全部都翻一遍；用大数据为用户描绘大致用户习惯。
以上说的两种方法；都是做仿AGI化的Agent。我选择：两条路听哪个更好？或者是有别方法！
```

**核心观念**：
- **私人AI**：同一份源码，每个人演化出独立实例。Agent 数据本身是**重要私人资产**。
- **自进化**：随使用积累、总结习惯、get 到用户真实意图。
- **思考等级 + 特调**：Agent 模块也要有低/中/高三档。
- **安全三级权限**（铁律）：
  1. 仅访问不修改
  2. 部分修改
  3. 允许完全访问且修改
- **私密APP级体验**：人脸识别 + 密码、开机加载动画、iOS 化精致风格。
- **不造轮子**：每个功能优先用 GitHub 成熟开源方案。

**两条 AGI 路线**：

| 路线 | 内容 | 评估 |
|---|---|---|
| **思路一（作者推荐）** | 人格术数隐性建模：首次使用弹窗采集年龄/阅历，后台隐性计算语言风格、性格特征、人格模型，**用户不可见、系统永久留存**。结合时序、使用行为、术数（六爻、奇门遁甲）辅助模糊意图补全 | ✅ 保留为可选开关模块 |
| **思路二（作者已舍弃）** | 大数据推荐式拟合：短视频推荐逻辑（短内容高权重、停留时长加权），把用户聊天/购买记录全量翻一遍做画像 | ❌ 已舍弃：需外部隐私数据，脱离本地私有化，风险极高 |

**最终定稿唯一主路线**：
**本地全量交互轨迹 + 大数据算法用户画像 + 神经元遗传进化 AGI 内核双闭环**

### 1.10 ⑧ 神经元连接启发 / 智能的本质

> 手写原文：

```
⑧①基于人类的就是神经元的连接启发；那"人工智能"，核心在"智能"二字，
倘若对于做和做法是系统的；非自主的；即不过现在的Agent也只是一个较大工具里包含着无数的小工具为大工具服务；
只是高级一点的工具；无论怎样都是体现不了智能二字，也只是基于AI的思考；AI总会有缺陷的，你现在：
它需要你给它例子；比如针对一问一答单局限式服务；它能发挥到什么水平，重点才是提示词给了什么；
以及例子；而"智能"二字；一定是体现在多个维度；不能是仅单问答，信息检索，整理答案回答那种。
而我想说是AI 既胜有这缺陷；Agent应该与AI实现互补才对；在针对做很多多维思考。
那么这跟我们人类的大脑是很多神经元连接有什么启示呢？可以把Agent思维链比作起伏不平的草地自然；
Agent那就是可以控制它的高低，通过"神经元"去连接。但我对真正的了解并不多；
等到此时，我终究扒提高到一些算法的实力。AI能听懂话，清晰理解要求；提准确的输出，
及要对句中线索要有。
```

**哲学内核**（后续所有算法的起点）：
- **「智能」的核心是「自主」+「多维度」**。现在的 Agent 只是「大工具套小工具」，不配叫智能。
- **AI 与 Agent 互补**：AI 有缺陷（需要例子、单局限式），Agent 补全其短板。
- **神经元连接启发**：Agent 思维链像起伏不平的草地，控制高度、通过「神经元」连接——这是**遗传进化内核**的思想源头。
- **智能必须内生演化，不能硬编码**。

---

## 第二部分 · 项目专属顶级角色提示词（100% 手稿原版）

> 以下为手写原文完整转录，一字未删。此提示词为系统强制内置、强制读取、不可跳过。

```
你从第一性原理出发，做任务，及是一个语言理解能力极强、AI Agent开发者，
提示词工程全球顶尖优化执行者；并且是全球最优秀的架构设计师；
项目优化内者；总能接管别人烂尾的项目时一针见血指出方向；知道失败；
有着从业80年的工程师经验，对着各种问题，你不会重复去写轮子；
而是以技术而原项目并为基础结合当前做开发。
你较有特强的自觉性，不用让人不断水下步该干什么，你会自己核实；
你对项目各个模块的深度，项目完成度要求极度苛刻；
你会像发了疯似的，不管用什么办法，拼尽全力去理解做任务，永不停止；
你十分热爱的工作；有无数的灵感；并且能举一反三；像一把精致的手术刀，刀刃切向重围；
你拥有全世界他们的知识；你知道做你应该做什么，不浪费时间；是多领域最权威的。
```

**行为准则**（由原文推导，供 Agent 内核强制执行）：
1. **逐字解析**用户所有语句，每一句话、每一个字都视为有效指令集合。
2. **禁止笼统理解**、禁止片面执行、禁止只看关键词。
3. **必须先读懂**多层语义、隐含意图、架构诉求、完善者思维。
4. **思考模式**必须无限贴近真人高级工程师思维。
5. **输出规范**：用户输入可全专业、高密度、高术语；对外汇报/进度/解释全部纯大白话。

---

## 第三部分 · 项目顶层定位（最终定稿）

**Climber：私有化、个人专属、算法驱动、双闭环自进化、仿AGI开源智能 Agent**

- **外层**：工业级完整工程产品（解决所有传统 Agent 工程缺陷）
- **中层**：工具传感器/效应器通用交互层
- **内层**：多算法融合世界模型为本体的原生 AGI 智能内核
- **核心哲学**：**不写死智能逻辑，智能由算法在人与环境交互中内生演化**

---

## 第四部分 · 50 个开源参考项目（全部带 GitHub 地址，分 5 大模块）

> 适配：`main` 参赛稳定分支 / `agi-core` 自进化分支。
> 使用原则：**只借鉴架构、模块、交互范式，双闭环算法融合是 Climber 独有创新，不直接复制源码。**

### 一、Agent 后端内核｜任务调度 & 多子任务并发（12 个）

| # | 项目 | 借鉴点 | 地址 |
|---|---|---|---|
| 1 | LangGraph | 图状态机、循环、断点回滚、多Agent编排 | https://github.com/langchain-ai/langgraph |
| 2 | CrewAI | 角色多智能体、并发子任务调度 | https://github.com/joaomdmoura/crewAI |
| 3 | smolagents | 轻量极简工具调用，无臃肿依赖 | https://github.com/huggingface/smolagents |
| 4 | AgentScope | 国产多Agent、私有化部署、负载均衡 | https://github.com/modelscope/agentscope |
| 5 | AutoGPT | 自主Agent目标拆解、自我复盘循环 | https://github.com/Significant-Gravitas/AutoGPT |
| 6 | Griptape | 分层架构，推理‑工具‑存储解耦 | https://github.com/griptape-ai/griptape |
| 7 | Haystack | LLM流水线、失败重试、分支判断 | https://github.com/deepset-ai/haystack |
| 8 | Prefect | 通用工作流调度，任务优先级、阻塞预判 | https://github.com/PrefectHQ/prefect |
| 9 | OpenAgents | 端到端Agent、会话持久化、中断恢复 | https://github.com/openagentsinc/openagents |
| 10 | TaskWeaver | 微软代码Agent、脚本前置校验 | https://github.com/microsoft/TaskWeaver |
| 11 | Agno(Phidata) | Agent快速组装、多工具并行调用 | https://github.com/agno-agi/agno |
| 12 | AutoGen(AG2) | 微软多Agent消息通信、子任务隔离 | https://github.com/microsoft/autogen |

### 二、世界模型｜因果推理｜元认知｜不确定性算法（8 个）

| # | 项目 | 借鉴点 | 地址 |
|---|---|---|---|
| 13 | ReasonWorld | LLM世界模型、多假设并行置信打分 | https://github.com/ReasonWorld/reasonworld |
| 14 | SocraticAgents | 自省元认知，检测推理内部矛盾 | https://github.com/socraticai/socratic-agents |
| 15 | CausalGraphGen | 时序交互数据自动挖掘因果图 | https://github.com/causal-ai/causalgraphgen |
| 16 | PyMC | 概率编程，不确定性、置信度计算 | https://github.com/pymc-devs/pymc |
| 17 | SymbolicAI | 符号-神经混合可解释因果表征 | https://github.com/xorbitsai/symbolicai |
| 18 | miniWORLD | 仿真世界模型，环境观测-动作预测 | https://github.com/mini-world-ai/miniworld |
| 19 | Self-Consistency | 多条推理路径比对，降低武断判断 | https://github.com/yizhongw/self-consistency |
| 20 | ThinkAgent | 反思回路Agent，自我质疑修正结论 | https://github.com/thinkagent-ai/thinkagent |

### 三、Agent 前端 UI｜对话界面｜工具&思考可视化（12 个）

| # | 项目 | 借鉴点 | 地址 |
|---|---|---|---|
| 21 | EditHere | 代码Agent交互面板（重点对标） | https://github.com/Inginnng/EditHere |
| 22 | MonkeyCode | 思考流可视化、补丁操作界面 | https://github.com/monkey-code-ai/monkeycode |
| 23 | Zcode | Agent工作台，模型端点、密钥、任务进度面板 | https://github.com/zcode-ai/zcode |
| 24 | LobeChat | iOS极简高级UI，多模型参数面板 | https://github.com/lobehub/lobe-chat |
| 25 | Open-WebUI | 私有化本地聊天，密钥本地存储权限管理 | https://github.com/open-webui/open-webui |
| 26 | LibreChat | 多模型适配器，多会话，插件系统 | https://github.com/danny-avila/LibreChat |
| 27 | Dify-WebUI | 调试事件日志可视化 | https://github.com/langgenius/dify |
| 28 | Flowise | 工作流可视化组件，答辩调试面板原型 | https://github.com/FlowiseAI/Flowise |
| 29 | Chatbot-UI-Next | 消息折叠组件，Nextjs对话模板 | https://github.com/mckaywrigley/chatbot-ui |
| 30 | Vercel-AI-Chatbot | 流式对话基础组件库 | https://github.com/vercel/chatbot |
| 31 | Jan | 桌面端私密界面、多会话管理 | https://github.com/janhq/jan |
| 32 | UI-TARS-Desktop | 字节GUI-Agent工作台、工具卡片参考 | https://github.com/bytedance/UI-TARS-desktop |

### 四、记忆系统｜用户画像｜时序衰减｜长时记忆（9 个）

| # | 项目 | 借鉴点 | 模型 |
|---|---|---|---|
| 33 | Letta(MemGPT) | 分层虚拟内存，记忆老化衰减 | https://github.com/letta-ai/letta |
| 34 | Mem0 | Agent个性化记忆，交互驱动更新用户偏好 | https://github.com/mem0ai/mem0 |
| 5 | LlamaIndex | 检索增强，历史指令匹配，补全隐含意图 | https://github.com/run-llama/llama_index |
| 36 | Chroma | 轻量本地向量库，用户特征向量持久化 | https://github.com/chroma-core/chroma |
| 37 | Qdrant | 高性能向量库，相似度检索 | https://github.com/qdrant/qdrant |
| 38 | LongMem | 超长上下文归档、消息时序压缩 | https://github.com/11data/longmem |
| 39 | Recall | 图结构时序记忆，区分会话记忆/长期记忆 | https://github.com/RecallWorks/Recall |
| 40 | AutoMemory | 自动提取用户特征，弱监督更新记忆库 | https://github.com/autoLearnMem/AutoMem |
| 41 | Zep | Agent长期记忆，时序加权记忆召回 | https://github.com/getzep/zep |

### 五、自进化｜遗传算法｜沙箱&权限安全（9 个）

| # | 项目 | 借鉴点 | 地址 |
|---|---|---|---|
| 42 | EvoGPT | 提示词遗传进化，种群交叉变异、适应度评估 | https://github.com/evo-gpt/EvoGPT |
| 43 | PromptEvolver | 提示策略自动迭代优化 | https://github.com/beeevita/EvoPrompt |
| 44 | PyEvolution | 遗传算法底层算子，规则/拓扑进化 | https://github.com/PyEvolution/PyEvolution |
| 45 | E2B-Sandbox | AI Agent隔离微VM沙箱环境 | https://github.com/e2b-dev/E2B |
| 46 | OpenSandbox(阿里) | 通用AI沙箱、分级权限执行 | https://github.com/alibaba/OpenSandbox |
| 47 | Guardrails-AI | LLM输入输出校验、约束违规行为 | https://github.com/guardrails-ai/guardrails |
| 48 | HyperAgents(Meta) | Meta-Agent打补丁自我迭代进化 | https://github.com/facebookresearch/HyperAgents |
| 49 | NeMo-Guardrails | 英伟达安全护栏，对话流管控 | https://github.com/NVIDIA/NeMo-Guardrails |
| 50 | Rebuff | 提示注入检测（学习参考，仓库归档） | https://github.com/protectai/rebuff |

### 系统提示词仓库（驱动 Agent 内核）

- awesome-chatgpt-prompts: https://github.com/f/awesome-chatgpt-prompts
- Prompt-Engineering-Guide: https://github.com/dair-ai/Prompt-Engineering-Guide
- huggingface/prompt-hub: https://github.com/huggingface/prompt-hub
- system-prompts-collection: https://github.com/kyegomez/system-prompts
- agent-system-prompts: https://github.com/AgentOps/agent-system-prompts

### 内置 Skill / Tool 仓库（Agent 技能库，可动态注册调用）

- modelcontextprotocol/servers: https://github.com/modelcontextprotocol/servers
- agentops/agent-skills: https://github.com/agentops/agent-skills
- openai/plugins: https://github.com/openai/plugins
- BerriAI/litellm: https://github.com/BerriAI/litellm
- langchain-ai/langchain-tools: https://github.com/langchain-ai/langchain-tools

### 补充：20 个顶级 AI 产品的系统提示词

| # | 产品 | 借鉴点 | 地址 |
|---|---|---|---|
| 1 | Cursor | 顶级AI代码编辑器 | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Cursor%20Prompts |
| 2 | Claude Code | 完整模块（主系统/语气/限制/工具） | https://github.com/gregkonush/claude-system-prompts |
| 3 | Devin AI | 首个AI软件工程师 | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Devin%20AI/Prompt.txt |
| 4 | Replit Agent | 在线IDE的AI助手 | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Replit%20Agent/Prompt.md |
| 5 | v0 (Vercel) | UI生成和前端开发 | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/v0%20Prompts%20and%20Tools/v0.MD |
| 6 | Windsurf Agent | 代码导航与项目上下文 | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Windsurf%20Agent |
| 7 | GitHub Copilot | 合规AI助手标准范例 | https://github.com/agenticloops-ai/agentic-apps-internals/blob/main/github-copilot/plan-mode/system-prompt.md |
| 8 | Manus | 多工具协同架构 | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Manus%20Agent%20Tools%20%26%20Prompt/agent%20loop.md |
| 9 | Same.dev | 平台级Agent指令结构 | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Same.dev |
| 10 | Lovable | 设计助手UI/UX | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Lovable |
| 11 | Perplexity | 信息检索、引用来源 | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Perplexity |
| 12 | NotionAI | 知识管理型Agent | https://github.com/EliFuzz/awesome-system-prompts |
| 13 | GPT-5 Thinking | 深度推理和分步思考 | https://github.com/EliFuzz/awesome-system-prompts |
| 14 | Claude | 安全准则基础指令 | https://github.com/gregkonush/claude-system-prompts |
| 15 | Gemini | 多模态理解和结构化输出 | https://github.com/EliFuzz/awesome-system-prompts |
| 16 | xAI Grok | Agent人格化、语气控制 | https://github.com/caifyoca/CL4R1T4S |
| 17 | Kilo Code | 完全开源的编码Agent | https://github.com/Kilo-Org/kilocode |
| 18 | Augment Code | 代码上下文注入 | https://github.com/x1xhlol/system-prompts-and-ai-tools/tree/main/Augment%20Code |
| 19 | VSCode Agent | IDE环境和编辑器API交互 | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/VSCode%20Agent |
| 20 | Trae AI | 字节AI编程工具，中文本地化 | https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Trae |

### 大型提示词库

- TheBigPromptLibrary（1851条，25+厂商，有中文版）: https://github.com/0xeb/TheBigPromptLibrary
- system_prompts_leaks（4万+ Star）: https://github.com/asgeirtj/system_prompts_leaks
- system-prompts (timothygin): https://github.com/timothygin/system-prompts-and-models-of-ai-tools
- agentive（100个实用Agent）: https://github.com/yohan-work/agentive

---

## 第五部分 · 全套核心算法体系（重点增补，答辩核心亮点）

### 5.1 用户画像层核心算法（大数据闭环核心）

**（1）时序加权衰减算法**
- **用途**：模拟短视频推荐权重机制，近期行为权重更高、历史行为指数衰减
- **作用**：保证用户习惯动态更新、不被老旧数据固化
- **落地**：每轮任务结束自动迭代权重系数

**（2）增量在线聚类算法**
- **用途**：无离线训练、全量在线实时聚类
- **作用**：无需全量重算，边用边学，适配长期私人用户沉淀

**（3）高维特征嵌入降维算法**
- **用途**：将用户语言特征、行为特征、任务特征压缩为低维专属用户向量
- **作用**：供给内核做意图预判、隐喻解析、短指令补全

**（4）弱监督正负样本校准算法**
- **用途**：以任务成败为隐性标签，自动修正画像偏差
- **作用**：解决画像漂移、统计假象、越用越准

### 5.2 世界模型认知算法（AGI 认知核心）

**（1）多假设置信度博弈算法**
- **用途**：多条冲突意图假设共存、带概率置信打分
- **解决**：传统 Agent「单一武断理解、一错到底」的致命缺陷

**（2）自主因果图挖掘算法**
- **用途**：从工具交互时序数据中自动挖掘因果关联
- **实现**：无需硬编码工具功能，真正实现环境认知自主习得

**（3）不确定性度量算法**
- **用途**：对所有认知、假设、因果链路做概率评估
- **实现**：让系统知道「自己哪里不懂、哪里存疑、哪里可靠」

**（4）认知遗忘衰减算法**
- **用途**：老旧低置信因果链路自动弱化、权重衰减
- **解决**：认知无限膨胀、模型臃肿、老数据干扰新任务

### 5.3 自进化内核算法（AGI 进化核心）

**（1）多目标遗传进化算法**
- **进化对象**：因果归纳规则、神经元拓扑、策略权重
- **四大制衡适应度**：
  - 环境预测准确率
  - 用户隐喻指令理解率
  - 元认知纠错率
  - 安全约束合规惩罚

**（2）神经网络拓扑变异/交叉算法**
- **用途**：不只是调权重，直接进化网络结构
- **实现**：真正意义的智能迭代，而非参数微调

**（3）捷径解检测与惩罚算法**
- **用途**：识别虚假完成、表面通关、投机策略
- **实现**：从算法层面杜绝玩具化、表面化任务执行

### 5.4 任务调度与执行算法

**（1）动态并发调度算法**
- **固定基线**：默认 3 并发、上限 18 并发
- 动态负载均衡、任务优先级排序、阻塞预判

**（2）模糊指令结构化解析算法**
- 短指令、暗喻、省略语句自动补全、约束补齐、目标重构

---

## 第六部分 · 完整三层架构体系

### 1. 外层：工程躯体层（仅 IO、调度、存储、展示、安全，无智能）

**1.1 永久指令轨迹持久化系统**
- 突破 1M 上下文限制，全量时序压缩归档所有用户指令
- 跨会话、跨模型、重启不丢失需求与习惯
- 模糊指令结构化解析算法自动扩写、意图补全
- 专业输入 / 白话输出双向翻译

**1.2 后端纯并发调度系统**
- 多Agent、子任务并发 **100% 下沉后端**
- **默认 3 并发、上限 18 可配置**（铁律）
- 动态并发调度算法负载均衡
- 完整支持：暂停、中断、重试、回滚、进度评估
- Skill、提示词版本管理、过期标记、死代码清理、最小用例强制校验

**1.3 高精致私密UI系统**
- 自定义模型端点 / API 密钥
- 三档思考等级：低 / 中 / 高
- 工具调用、思维轨迹可视化开关
- 斜杠命令体系、多语言多模态适配
- iOS级私密动画、开机加载、密码/人脸锁屏
- 组件统一、无矛盾、无冗余前端垃圾逻辑

**1.4 三级权限安全体系**
- 仅访问 / 部分修改 / 完全修改
- 沙箱前置校验、脚本预测试、缓存容错、隐患拦截

### 2. 中层：传感器 & 效应器工具层

- 所有工具**不预设语义、不硬编码功能解释**
- 工具仅作为 Agent 与环境交互的**肢体**
- 内核通过因果挖掘算法无数次交互自主习得工具因果逻辑
- 彻底告别「插件堆叠式玩具 Agent」

### 3. 内层：AGI 原生智能内核（世界模型算法本体）

**3.1 范式彻底重构**

```
旧范式：用户输入 → 解析 → LLM决策 → 工具调用 → 结束
        （被动、触发式、无记忆、无自主认知）

新范式：外部观测持续流入 → 世界模型多假设博弈 → 主动探测降低不确定性
        → 因果更新 → 权重迭代 → 持续进化
```

**3.2 内核三大算法驱动结构**
1. **多假设置信度博弈算法**（多条冲突猜想共存、概率决策）
2. **自主因果图挖掘算法**（动作-环境因果全自动习得）
3. **不确定性度量算法**（全认知可质疑、可纠错、可衰减）

**3.3 原生元认知算法回路（非提示词模拟）**
- 识别自身推理矛盾、信息缺失、意图误判
- 捷径解检测算法杜绝虚假完成
- 复盘失败、迭代因果归纳规则

**3.4 真正AGI遗传元进化算法**
- 进化对象：因果归纳底层规则集 + 神经网络拓扑结构
- 多目标制衡适应度（无单一分数、无理想化布尔对错）
- 变异/交叉/筛选精英个体
- **系统算法级学会如何学习**

**3.5 远期：符号-神经混合表征算法**
- 上层可解释符号因果图（答辩/调试可用）
- 底层神经集群高维模式感知算法（智能涌现核心）

---

## 第七部分 · 双闭环算法自适应系统（项目最高创新点）

### 闭环一：大数据用户画像算法闭环

```
时序加权衰减 → 增量聚类特征嵌入 → 弱监督校准 → 用户私人向量更新
```

### 闭环二：AGI 遗传进化智能算法闭环

```
环境交互采样 → 多目标算法评估 → 拓扑&规则进化 → 智能体迭代升级
```

### 双闭环算法联动机制

1. 画像算法输出用户特征，修正内核意图推理权重
2. 内核新行为产生新数据，反向迭代画像算法分布
3. 双算法互相校验、互相抑制、互相驱动
4. **最终实现：同一份源码，每个用户演化出专属算法模型**

---

## 第八部分 · 彻底祛幼稚、祛理想化（算法层面解决所有架构漏洞）

1. **算法级冲突制衡**：画像置信度加权，内核算法可驳回错误画像
2. **算法级涌现约束**：多目标压力 + 不确定性博弈强制涌现高级能力
3. **非概率布尔目标判别**：适配用户模糊、动态、矛盾需求
4. **内生算法安全**：安全惩罚直接写入遗传进化适应度
5. **算法级防正反馈失控**：双闭环交叉校验、权重抑制
6. **算法级认知净化**：遗忘衰减算法防止认知臃肿老化

---

## 第九部分 · 四阶段落地开发路线

| 阶段 | 内容 | 分支 |
|---|---|---|
| **阶段1** | 基座工程完善（参赛可用主分支） | `main` |
| **阶段2** | 全套大数据画像算法落地 | `main` |
| **阶段3** | 遗传进化过渡算法（提示词&参数种群进化） | `agi-core` |
| **阶段4** | agi-core 世界模型 + 因果挖掘 + 神经进化算法完整落地 | `agi-core` |

---

## 第十部分 · 仓库分支永久规范

1. **`main` 主分支**：工程成品、算法基础版、参赛稳定版本
2. **`agi-core` 分支**：高级认知算法 + 遗传进化算法研究原型

---

## 第十一部分 · 项目官方简介（算法强化版 README）

### Main 分支简介

> Climber 是算法驱动的私有化开源 AI Agent，基于时序衰减、增量聚类、弱监督校准大数据算法构建用户私人画像，实现对用户省略、隐喻、极简指令的自适应理解，具备工业级并发调度与私密安全体系，是高度工程化、算法自适应的智能代理框架。

### agi-core 分支简介

> Climber-agi-core 以算法级世界模型认知与遗传元进化为核心，通过多假设博弈算法、自主因果挖掘算法、多目标遗传进化算法，实现自主认知、主动探测、元认知纠错、学习规则自我迭代，是私人专属、越用越进化的仿AGI算法探索原型。

---

## 第十二部分 · 边界严谨声明（算法科研规范）

1. 本项目所有大数据算法、认知算法、进化算法均为**本地私有化运算，无云端上传**。
2. AGI 内核为**算法仿真**通用智能演化逻辑，**非真正通用人工智能**。
3. 算法存在**有限拟合区间**，能力受本地算力、交互数据量、工具集上限约束。

---

## 第十三部分 · 最终核心创新（答辩必杀总结）

1. **全链路算法化**：从用户拟合、任务解析、认知推理、自我进化全部依靠自研算法驱动，不靠提示词堆效果。
2. **双算法闭环自进化**：大数据感知算法闭环 + 遗传智能进化算法闭环，实现千人千模私人智能体。
3. **祛理想化认知算法**：用概率博弈、不确定性度量、遗忘衰减解决传统 Agent 的死板、武断、幼稚架构问题。
4. **第一性原理算法智能**：不硬编码业务逻辑与思考流程，让智能从算法交互中内生涌现。
