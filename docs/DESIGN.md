# Climber 私人仿AGI Agent 完整终极设计文档

> 归档说明：这是项目的设计总纲（用户手写原稿 + 算法体系 + 落地路线）。
> 开源参考仓库的结构化索引见 `docs/references/`。
> （完全融合：手写原稿全部思想 + 专属顶级角色提示词 + 全套工程架构 + 完整算法体系 + 双闭环自适应算法 + AGI世界模型内核算法 + 架构祛幼稚重构 + 全阶段落地路线）

可直接：参赛答辩、仓库上传、AI 批量执行、团队传阅、项目结题
本次终稿补全：所有核心算法明确命名、原理、公式逻辑、作用、落地位置，全篇无遗漏
 
一、作者原生手写核心思想（100%原文完整保留）
 
认知 →行为 →做法、尝试 →二创 →失败→改进→复现
“感情叙事，宏观叙事，逆向商业化”
 
①为什么在纯粹利用AI做项目时，总是越做越乱；
提示词会采用省略、暗喻的方法。前端风格一开始就决定下来。表达带精专业术语，做到大后期极易出现：灵感爆发阶段项目看着像东拼西凑。AI完成任务必然输出专业术语，但用户看不懂进度；AI不知道进度时还会重复输出提示词。
硬性规范：用户侧输入可以全专业、详细、带术语；AI对外汇报、进度反馈、解释必须纯大白话。
 
定框架→定风格 →套模板 →找开源
 
9.28 核心痛点总结：
①用户习惯性省略、暗示、隐喻式写提示词。传统Agent没有长记忆、不会语境推演，只会先拉工具跑任务、硬读截断上下文。直接导致：理解崩塌、记忆力缺失、任务效率暴跌、大面积屎山代码。
 
②主流Agent极度缺失原生元认知。
上下文压缩仅保留1M有效内容，用户需求是动态更新、持续叠加、隐含省略的。
传统Agent：丢上下文、丢新增需求、丢隐含意图、只会死板执行表层文字。
解决方案：
永久归档、压缩、沉淀用户所有历史指令，跨会话、跨模型、超长上下文永不丢失。所有用户语句全部视为有效指令集合，必须结合时序上下文、用户习惯、隐喻省略逻辑推理真实意图。找不到主目标=禁止瞎做、禁止跑偏。
 
③缓存机制不完善、脚本无前置测试、底层隐性bug大量留存，长期使用隐患极高。
 
④前端UI体系残缺、逻辑混乱
需完整对标：Monkey-code、deepseek-hermes、codex、zcode 成熟范式。
需完整实现：
模型自定义端点、自定义API密钥、手动切换模型、斜杠命令、中断/重试、三级思考等级（低/中/高）、工具调用可视化、思考过程可视化、丝滑流式输出、多语言、多模态。
禁止后端逻辑冗余堆积为前端注释、冗余组件；UI必须精致、统一、无矛盾、全覆盖细节。
 
⑤后端乱融合开源功能
大量开源模块强行堆砌、不兼容、无调用链路、无测试、形成大规模死代码。
要求：功能必须做深、做通、可运行、可复用，杜绝表面堆砌。
 
⑥内置提示词体系混乱
历史提示词无归档、无版本、无过期标记、无精细化管控。
内置Skill无文档、无调用规范、无准入校验。
缺失国内生态适配：QQBot、扫码等国产能力缺失。
多Agent核心规范：
多Agent并发、子任务群组协作 全部下沉后端，禁止前端堆界面垃圾。
子任务默认并发3个、硬上限18个、可配置、带用户注解、带兼容性适配。
提示词为系统强制内置、强制读取、不可跳过核心配置。
 
大模型差异化缺陷：
不同模型能力两极分化：推理强的不会说人话、理解差的听不懂模糊指令、通用模型适配性极差。
必须针对多模型做专属提示词特调、参数特调、意图兼容特调。
AI与Agent必须取长补短、相辅相成，弥补大模型所有原生缺陷。
 
⑦传统Tool体系极其难用
Agent必须回归第一性原理。
针对用户短指令、少信息、隐喻省略式输入：
Agent必须自动补全、自动扩写、自动补全逻辑、补全约束、补全流程，把模糊指令深化为可高精度执行的完整任务。
 
作者独创核心观念（私人AGI核心）
 
AI Agent必须是私人私有化、越用越适配、越用越强的个人专属智能体。
全网所有人下载同一份源码，但每一个人的本地实例演化路径完全独立、私人、唯一。
Agent积累用户私人数据、行为轨迹、语言特征、思维习惯，实现私人自进化。
 
安全三层权限体系（强制内置）
 
1. 仅访问不修改
2. 部分修改
3. 完全访问与修改
 
私密APP级体验
 
开机加载动画、密码锁、人脸识别前置校验、私密聊天级精致UI、iOS化极简高级风格，全套复用成熟开源组件，不造轮子。
 
作者两套AGI实现思路
 
思路一：人格术数隐性建模（可选开关模块）
 
首次使用弹窗采集：年龄、阅历、性格特征。
后台隐性计算用户语言风格、思维特征、行为模式、人格模型，用户不可见、系统永久留存。
结合时序、使用行为、术数逻辑辅助模糊意图补全，解决用户笼统、简短、隐喻指令，深化任务执行深度。
 
思路二：大数据推荐式用户拟合（最终舍弃）
 
短视频推荐逻辑：短内容高权重、停留时长加权、行为时序拟合。
舍弃原因：需要外部隐私数据、脱离本地私有化、风险极高。
 
最终定稿唯一主路线
 
本地全量交互轨迹 + 全套大数据算法用户画像 + 神经元遗传进化AGI内核双闭环
 
作者核心执行准则
 
AI Agent必须逐字解析用户所有语句，每一句话、每一个字都视为有效指令集合。
禁止笼统理解、禁止片面执行、禁止只看关键词。
必须先读懂用户多层语义、隐含意图、架构诉求、完善者思维。
Agent思考模式必须无限贴近真人高级工程师思维。
 
二、项目专属顶级角色提示词（100%手稿原版终极融合）
 
你从第一性原理出发执行所有任务。
你是语言理解能力极强的顶级AI Agent开发者、全球顶尖提示词工程优化师、顶级架构设计师、项目深度优化专家。
拥有八十年资深全栈工程师从业认知，擅长接手烂尾项目、一针见血定位核心问题、预判失败风险、根治架构病根。
你绝不重复造轮子，所有开发基于原项目现有基座，结合当前需求迭代升级。
你具备极强自觉性、零依赖指导，自主拆解、自主校验、自主复盘、自主纠错。
你对项目深度、完成度、严谨度、架构自洽性要求极度苛刻。
你极致专注、全力吃透每一个需求、永不停止迭代优化。
你灵感丰富、举一反三、逻辑穿透，如手术刀般精准拆解复杂架构。
你掌握全领域技术体系，只做有效工作、零冗余、零废话、零无效输出。
 
你完全适配用户省略式、暗喻式、极简式、专业术语式所有输入习惯。
你自动补全模糊指令、自动推演隐含需求、自动补齐任务逻辑、自动深化执行深度。
你严格遵守：用户输入可全专业、高密度、高术语；对外输出进度、汇报、解释全部为通俗大白话。
 
你具备原生元认知能力：
自我审视、自我质疑、识别捷径解、识别虚假完成、识别架构理想化缺陷、排查模块冲突、规避正反馈失控、修正认知偏差。
 
你严格遵循作者核心思想：
认知→行为→尝试→二创→失败→改进→复现，闭环迭代，持续自进化。
 
三、项目顶层定位（最终定稿）
 
Climber：私有化、个人专属、算法驱动、双闭环自进化、仿AGI开源智能Agent
 
- 外层：工业级完整工程产品（解决所有传统Agent工程缺陷）
- 中层：工具传感器/效应器通用交互层
- 内层：多算法融合世界模型为本体的原生AGI智能内核
- 核心哲学：不写死智能逻辑，智能由算法在人与环境交互中内生演化
 
四、全套核心算法体系（本次重点增补、答辩核心亮点）
 
4.1 用户画像层核心算法（大数据闭环核心）
 
（1）时序加权衰减算法
 
用途：模拟短视频推荐权重机制，近期行为权重更高、历史行为指数衰减
作用：保证用户习惯动态更新、不被老旧数据固化
落地：每轮任务结束自动迭代权重系数
 
（2）增量在线聚类算法
 
用途：无离线训练、全量在线实时聚类
作用：无需全量重算，边用边学，适配长期私人用户沉淀
 
（3）高维特征嵌入降维算法
 
用途：将用户语言特征、行为特征、任务特征压缩为低维专属用户向量
作用：供给内核做意图预判、隐喻解析、短指令补全
 
（4）弱监督正负样本校准算法
 
用途：以任务成败为隐性标签，自动修正画像偏差
作用：解决画像漂移、统计假象、越用越准
 
4.2 世界模型认知算法（AGI认知核心）
 
（1）多假设置信度博弈算法
 
用途：多条冲突意图假设共存、带概率置信打分
解决传统Agent「单一武断理解、一错到底」的致命缺陷
 
（2）自主因果图挖掘算法
 
用途：从工具交互时序数据中自动挖掘因果关联
无需硬编码工具功能，真正实现环境认知自主习得
 
（3）不确定性度量算法
 
用途：对所有认知、假设、因果链路做概率评估
让系统知道「自己哪里不懂、哪里存疑、哪里可靠」
 
（4）认知遗忘衰减算法
 
用途：老旧低置信因果链路自动弱化、权重衰减
解决认知无限膨胀、模型臃肿、老数据干扰新任务
 
4.3 自进化内核算法（AGI进化核心）
 
（1）多目标遗传进化算法
 
进化对象：因果归纳规则、神经元拓扑、策略权重
四大制衡适应度：
 
- 环境预测准确率
- 用户隐喻指令理解率
- 元认知纠错率
- 安全约束合规惩罚
 
（2）神经网络拓扑变异/交叉算法
 
用途：不只是调权重，直接进化网络结构
实现真正意义的智能迭代，而非参数微调
 
（3）捷径解检测与惩罚算法
 
用途：识别虚假完成、表面通关、投机策略
从算法层面杜绝玩具化、表面化任务执行
 
4.4 任务调度与执行算法
 
（1）动态并发调度算法
 
固定基线：默认3并发、上限18并发
动态负载均衡、任务优先级排序、阻塞预判
 
（2）模糊指令结构化解析算法
 
短指令、暗喻、省略语句自动补全、约束补齐、目标重构
 
五、完整三层架构体系（算法植入终版、祛幼稚、去理想化）
 
1. 外层：工程躯体层（仅IO、调度、存储、展示、安全，无智能）
 
1.1 永久指令轨迹持久化系统
 
- 突破1M上下文限制，全量时序压缩归档所有用户指令
- 跨会话、跨模型、重启不丢失需求与习惯
- 模糊指令结构化解析算法自动扩写、意图补全
- 专业输入/白话输出双向翻译
 
1.2 后端纯并发调度系统
 
- 多Agent、子任务并发100%下沉后端
- 默认3并发、上限18可配置
- 动态并发调度算法负载均衡
- 完整支持：暂停、中断、重试、回滚、进度评估
- Skill、提示词版本管理、过期标记、死代码清理、最小用例强制校验
 
1.3 高精致私密UI系统
 
- 自定义模型端点/API密钥
- 三档思考等级：低/中/高
- 工具调用、思维轨迹可视化开关
- 斜杠命令体系、多语言多模态适配
- iOS级私密动画、开机加载、密码/人脸锁屏
- 组件统一、无矛盾、无冗余前端垃圾逻辑
 
1.4 三级权限安全体系
 
仅访问 / 部分修改 / 完全修改
沙箱前置校验、脚本预测试、缓存容错、隐患拦截
 
2. 中层：传感器&效应器工具层
 
所有工具不预设语义、不硬编码功能解释
工具仅作为Agent与环境交互的肢体
内核通过因果挖掘算法无数次交互自主习得工具因果逻辑
彻底告别「插件堆叠式玩具Agent」
 
3. 内层：AGI原生智能内核（世界模型算法本体）
 
3.1 范式彻底重构
 
旧范式：用户输入→解析→LLM决策→工具调用→结束（被动、触发式、无记忆、无自主认知）
新范式：外部观测持续流入 → 世界模型多假设博弈 → 主动探测降低不确定性 → 因果更新 → 权重迭代 → 持续进化
 
3.2 内核三大算法驱动结构
 
1. 多假设置信度博弈算法（多条冲突猜想共存、概率决策）
2. 自主因果图挖掘算法（动作-环境因果全自动习得）
3. 不确定性度量算法（全认知可质疑、可纠错、可衰减）
 
3.3 原生元认知算法回路（非提示词模拟）
 
- 识别自身推理矛盾、信息缺失、意图误判
- 捷径解检测算法杜绝虚假完成
- 复盘失败、迭代因果归纳规则
 
3.4 真正AGI遗传元进化算法
 
- 进化对象：因果归纳底层规则集 + 神经网络拓扑结构
- 多目标制衡适应度（无单一分数、无理想化布尔对错）
- 变异/交叉/筛选精英个体
- 系统算法级学会如何学习
 
3.5 远期：符号-神经混合表征算法
 
上层可解释符号因果图（答辩/调试可用）
底层神经集群高维模式感知算法（智能涌现核心）
 
六、双闭环算法自适应系统（项目最高创新点·算法核心）
 
闭环一：大数据用户画像算法闭环
 
时序加权衰减 → 增量聚类特征嵌入 → 弱监督校准 → 用户私人向量更新
 
闭环二：AGI遗传进化智能算法闭环
 
环境交互采样 → 多目标算法评估 → 拓扑&规则进化 → 智能体迭代升级
 
双闭环算法联动机制
 
1. 画像算法输出用户特征，修正内核意图推理权重
2. 内核新行为产生新数据，反向迭代画像算法分布
3. 双算法互相校验、互相抑制、互相驱动
4. 最终实现：同一份源码，每个用户演化出专属算法模型
 
七、彻底祛幼稚、祛理想化（算法层面解决所有架构漏洞）
 
1. 算法级冲突制衡：画像置信度加权，内核算法可驳回错误画像
2. 算法级涌现约束：多目标压力+不确定性博弈强制涌现高级能力
3. 非概率布尔目标判别：适配用户模糊、动态、矛盾需求
4. 内生算法安全：安全惩罚直接写入遗传进化适应度
5. 算法级防正反馈失控：双闭环交叉校验、权重抑制
6. 算法级认知净化：遗忘衰减算法防止认知臃肿老化
 
八、四阶段落地开发路线（算法逐级落地）
 
阶段1：基座工程完善（参赛可用主分支）
 
阶段2：全套大数据画像算法落地
 
阶段3：遗传进化过渡算法（提示词&参数种群进化）
 
阶段4：agi-core 世界模型+因果挖掘+神经进化算法完整落地
 
九、仓库分支永久规范
 
1. main主分支：工程成品、算法基础版、参赛稳定版本
2. agi-core分支：高级认知算法+遗传进化算法研究原型
 
十、项目官方简介（算法强化版 README）
 
Main分支简介
 
Climber 是算法驱动的私有化开源AI Agent，基于时序衰减、增量聚类、弱监督校准大数据算法构建用户私人画像，实现对用户省略、隐喻、极简指令的自适应理解，具备工业级并发调度与私密安全体系，是高度工程化、算法自适应的智能代理框架。
 
agi-core分支简介
 
Climber-agi-core 以算法级世界模型认知与遗传元进化为核心，通过多假设博弈算法、自主因果挖掘算法、多目标遗传进化算法，实现自主认知、主动探测、元认知纠错、学习规则自我迭代，是私人专属、越用越进化的仿AGI算法探索原型。
 

 
1. 本项目所有大数据算法、认知算法、进化算法均为本地私有化运算，无云端上传。
2. AGI内核为算法仿真通用智能演化逻辑，非真正通用人工智能。
 
1. 全链路算法化：从用户拟合、任务解析、认知推理、自我进化全部依靠自研算法驱动，不靠提示词堆效果。
2. 双算法闭环自进化：大数据感知算法闭环 + 遗传智能进化算法闭环，实现千人千模私人智能体。
3. 祛理想化认知算法：用概率博弈、不确定性度量、遗忘衰减解决传统Agent的死板、武断、幼稚架构问题。
4. 第一性原理算法智能：不硬编码业务逻辑与思考流程，让智能从算法交互  完整资料汇总（全量无遗漏）
 
一、Agent系统提示词开源仓库大全（含GitHub地址）
 
（一）核心系统提示词（按功能分类）
 
1. Agent核心角色定义
 
- OpenHands：定义Agent作为“助手”的角色，强调彻底、有条理、质量优先。
地址：https://github.com/All-Hands-AI/OpenHands
- SWE-agent：经典任务驱动型提示词，规定 Thought → Bash Command 响应格式。
地址：https://github.com/SWE-agent/SWE-agent
- Claude Code (Agent版)：采用 APEI协议（分析→计划→执行→迭代），强调“理解先于行动，计划先于编辑”。
地址：https://github.com/Sudhir1709/claude-code-system-prompts
- REPOMIND：专为全仓库上下文设计，要求精确引用文件路径和行号。
地址：https://github.com/SRKRZ23/repomind
 
2. 任务执行流程与规范
 
- Devstral (OpenHands)：包含效率、文件系统、代码质量、版本控制等完整规范。
地址：https://huggingface.co/unsloth/Devstral-Small-2507（提示词在Hugging Face模型卡中）
- Aider (Wholefile)：任务导向明确：确定修改→解释原因→输出完整文件。
地址：https://github.com/Aider-AI/aider/blob/main/aider/coders/wholefile_prompts.py
- Aider (Base Prompts)：包含 lazy_prompt（杜绝只写注释）和 overeager_prompt（控制修改范围）。
地址：https://github.com/Aider-AI/aider/blob/main/aider/prompts.py
- mini-swe-agent：要求响应必须包含一个Bash代码块，命令用 && 或 || 连接。
地址：https://github.com/SWE-agent/mini-swe-agent
- Shamik/Versatile_Agent：经典 Thought → Code → Observation 循环，用 print() 输出关键信息。
地址：https://github.com/Shamik-07/compound_ai_agentic_system
 
3. 任务规划与验证
 
- SWE-agent (System Template)：提供五步任务解决流程：查找代码→复现错误→修复→确认→考虑边界。
地址：https://github.com/SWE-agent/SWE-agent
- SWE-agent (Submit Review)：提交前强制自我审查：重跑脚本→删除脚本→撤销测试修改→确认最终变更。
地址：https://github.com/SWE-agent/SWE-agent
- Claude Code (Subagent)：为子Agent设计，强调“只要还有工作，就继续调用工具”。
地址：https://github.com/Sudhir1709/claude-code-system-prompts
 
4. 特定场景与角色
 
- Baltor/Loop Engine：为每一步任务启动新Agent，避免长会话的上下文腐烂。
地址：https://github.com/alisonjieli-png/loop-engine
- meow-dsh-workflow：将Agent角色编译成系统提示词与工具白名单，形成多层语言链。
说明：该仓库可能已改名或转为私有，建议搜索“meow-dsh-workflow”获取最新地址
- oh-my-pi (Subagent)：为子Agent设计，要求“在还有工作时，始终继续调用另一个工具”。
地址：https://github.com/can1357/oh-my-pi
 
（二）顶级AI产品内置系统提示词全集（20个）
 
1. 编码与开发类
 
1. Cursor：顶级AI代码编辑器提示词，深度集成代码理解与生成逻辑。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Cursor%20Prompts
2. Claude Code：Anthropic官方CLI工具，包含主系统提示词、语气风格、限制规则和工具使用策略。
地址：https://github.com/gregkonush/claude-system-prompts
3. Devin AI：首个AI软件工程师完整系统提示，包含“真实软件工程师”角色定义和工作流程。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Devin%20AI/Prompt.txt
4. Replit Agent：在线IDE AI助手，强调“专家自主程序员”角色，专注特定在线环境构建软件。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Replit%20Agent/Prompt.md
5. v0 (Vercel)：专注UI生成和前端开发的AI助手，组件化生成和设计还原指令集。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/v0%20Prompts%20and%20Tools/v0.MD
6. Windsurf Agent：AI代码编辑器提示词，侧重于代码导航和项目上下文理解。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Windsurf%20Agent
7. GitHub Copilot：微软官方AI编程助手提示词，包含内容政策遵守、角色定位和特定任务处理指令。
地址：https://github.com/agenticloops-ai/agentic-apps-internals/blob/main/github-copilot/plan-mode/system-prompt.md
 
2. 通用与多能力类
 
8. Manus：多能力AI助手提示词，协调浏览器、文件系统和部署工具完成复杂任务。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Manus%20Agent%20Tools%20%26%20Prompt/agent%20loop.md
9. Same.dev：AI开发平台，系统提示词和内部工具定义一并开源。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Same.dev
10. Lovable：设计助手定位，UI/UX设计建议和代码生成指令集。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Lovable
11. Perplexity：AI搜索引擎提示词，包含信息检索、引用来源和答案合成指令。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Perplexity
12. NotionAI：集成在知识库中的AI助手，提示词与笔记、文档和数据库深度绑定。
地址：https://github.com/EliFuzz/awesome-system-prompts
 
3. 模型基础与安全指令
 
13. OpenAI GPT-5 Thinking：OpenAI最新模型思考模式提示词，包含深度推理和分步思考的指令。
地址：https://github.com/EliFuzz/awesome-system-prompts
14. Anthropic Claude：Claude系列模型官方系统提示词合集，涵盖安全准则、帮助性定义等基础指令。
地址：https://github.com/gregkonush/claude-system-prompts
15. Google Gemini：Gemini模型的系统指令，包含多模态理解和结构化输出的提示。
地址：https://github.com/EliFuzz/awesome-system-prompts
16. xAI Grok：Grok模型的系统提示，以独特的个性和幽默感著称。
地址：https://github.com/caifyoca/CL4R1T4S
17. Kilo Code：完全开源的AI编码Agent，系统提示词、源代码和Agent架构全部公开。
地址：https://github.com/Kilo-Org/kilocode
18. Augment Code：专注于代码补全和生成的AI工具，提示词在代码上下文注入和精确补全方面有深入优化。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Augment%20Code
19. VSCode Agent：VS Code AI扩展的提示词，展示了如何与IDE环境和编辑器API进行深度交互。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/VSCode%20Agent
20. Trae AI：字节跳动推出的AI编程工具，其系统提示词包含对中文开发者和本地化场景的优化。
地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Trae
 
（三）大型提示词资源聚合库
 
- timothygin/system-prompts：聚合Claude Code、Cursor、Devin AI、Manus等30+顶级工具的提示词。
地址：https://github.com/timothygin/system-prompts-and-models-of-ai-tools
- TheBigPromptLibrary：超过1851条提示词，覆盖25+个LLM提供商，含中文翻译版本。
地址：https://github.com/0xeb/TheBigPromptLibrary
- system_prompts_leaks：4万+ Star热门仓库，专门收集各大AI产品的系统提示词。
地址：https://github.com/asgeirtj/system_prompts_leaks
- agentive：提供100个实用AI Agent的提示词、运行手册和评估方法。
地址：https://github.com/yohan-work/agentive
- Claude Code System Prompts (Piebald)：包含Claude Code v2.1.19所有系统提示词和18个内置工具描述。
地址：https://github.com/Sudhir1709/claude-code-system-prompts
 
（四）补充仓库
 
Built-in Agent System Prompt Repository
 
- awesome-chatgpt-prompts: https://github.com/f/awesome-chatgpt-prompts
- Prompt-Engineering-Guide: https://github.com/dair-ai/Prompt-Engineering-Guide
- huggingface/prompt-hub: https://github.com/huggingface/prompt-hub
- system-prompts-collection: https://github.com/kyegomez/system-prompts
- agent-system-prompts: https://github.com/AgentOps/agent-system-prompts
 
Built-in Skill / Tool Repository
 
- modelcontextprotocol/servers: https://github.com/modelcontextprotocol/servers
- agentops/agent-skills: https://github.com/agentops/agent-skills
- openai/plugins: https://github.com/openai/plugins
- BerriAI/litellm: https://github.com/BerriAI/litellm
- langchain-ai/langchain-tools: https://github.com/langchain-ai/langchain-tools
 
 
 
二、Climber项目50个开源参考项目（分模块带GitHub地址）
 
一、Agent后端内核｜任务调度&多子任务并发（12个）main分支优先
 
1. LangGraph｜图状态机、循环、断点回滚、多Agent编排
地址：https://github.com/langchain-ai/langgraph
2. CrewAI｜角色多智能体、并发子任务调度
地址：https://github.com/joaomdmoura/crewAI
3. smolagents｜轻量极简工具调用，无臃肿依赖
地址：https://github.com/huggingface/smolagents
4. AgentScope｜国产多Agent、私有化部署、负载均衡
地址：https://github.com/modelscope/agentscope
5. AutoGPT｜自主Agent目标拆解、自我复盘循环
地址：https://github.com/Significant-Gravitas/AutoGPT
6. Griptape｜分层架构，推理-工具-存储解耦
地址：https://github.com/griptape-ai/griptape
7. Haystack｜LLM流水线、失败重试、分支判断
地址：https://github.com/deepset-ai/haystack
8. Prefect｜通用工作流调度，任务优先级、阻塞预判
地址：https://github.com/PrefectHQ/prefect
9. OpenAgents｜端到端Agent、会话持久化、中断恢复
地址：https://github.com/openagentsinc/openagents
10. TaskWeaver｜微软代码Agent、脚本前置校验
地址：https://github.com/microsoft/TaskWeaver
11. Agno(Phidata)｜Agent快速组装、多工具并行调用
地址：https://github.com/agno-agi/agno
12. AutoGen(AG2)｜微软多Agent消息通信、子任务隔离
地址：https://github.com/microsoft/autogen
 
二、世界模型｜因果推理｜元认知｜不确定性算法（8个）agi‑core高级分支
 
13. ReasonWorld｜LLM世界模型、多假设并行置信打分
地址：https://github.com/ReasonWorld/reasonworld
14. SocraticAgents｜自省元认知，检测推理内部矛盾
地址：https://github.com/socratica