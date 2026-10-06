地址﻿https://github.com/lyn2010526-stack/climber﻿定位：私人化仿AGI Agent工程框架﻿﻿- 外层：完整工程产品（UI、API、多Agent、任务调度、安全、用户私人画像体系），解决现实工程全部痛点﻿- 内核：第一性原理目标求解 + 神经可进化内核，工具作为效应器/传感器，拒绝硬编码规划、记忆模块﻿- 核心哲学：不预设固定思考流程，只定义目标判别；
智能不是写死代码，是在与用户、环境交互中内生演化；
Agent是属于个人的、越用越适配使用者的私有智能载体﻿﻿整体分层总架构﻿﻿一、外层：产品工程外壳（解决你笔记全部工程痛点，全部现实业务层，不做决策推理）﻿﻿外壳只负责IO、调度、安全、展示、数据持久、多任务，不产生任何智能推理逻辑。
参考zcode、monkey‑code、deepseek‑hermes、codex成熟开源组件组装，不重复造轮子。
﻿﻿1. 指令解析层（解决笔记痛点①②⑦：省略、暗喻、短指令、上下文丢失、元认知缺失）﻿﻿- 接收用户原始输入：短句、暗喻、省略式口语、混杂专业术语的长文本全部原样收纳。
﻿- 持久保存全量用户指令轨迹库：压缩归档所有历史用户语句，不受上下文窗口1M限制；
切换模型、会话重置，目标与用户意图不会丢失。
﻿- 功能：对简略/隐喻用户输入做意图补全，把模糊简短用户表达扩写为完备内部任务规约；
把用户每一句话视作潜在指令集合，解析出主目标、约束、隐含条件；
区分：用户给的专业技术术语（内部使用），对外进度输出强制转为大白话。
﻿- 拒绝旧模式：不再上来直接调用工具，工具调用是内核输出的结果，不是解析层主动触发。
﻿﻿规避：找不到主目标就跑偏、上下文截断遗忘用户想法、提示词混乱堆砌。
﻿﻿2. 任务调度并发层（笔记痛点⑥）﻿﻿- 后端实现多Agent实例并行，多Agent、子任务并发全部放在后端，不在前端堆砌界面。
﻿- 默认并发子任务数3，上限18，可配置；
支持群组协作Agent；
支持中断、暂停、重试；
﻿- 内置任务完成度、准确度评估指标；
杜绝死代码，每个skill、子任务必须经过最小测试用例校验才允许启用。
﻿- 内置提示词版本管理：记录每版内置系统提示词，标记是否过期，可回滚。
﻿﻿3. UI交互层（笔记痛点④，iOS化精致私密APP体验）﻿﻿- 模型配置面板：自定义API端点、填入API‑key、切换模型；
﻿- 思考等级档位：低/中/高，控制内核推演深度；
﻿- 运行时可视化：可选展示工具调用、内部思维轨迹；
也可以隐藏；
支持命令行斜杠指令；
多模态、多语言支持；
﻿- 界面精致私密风格：开机加载动画、密码/人脸识别锁屏，私密应用交互范式；
﻿- 区分：后端能力不要冗余堆砌为前端注释、冗余UI组件；
UI只做展示与参数输入。
﻿﻿4. 安全权限层（笔记⑦）﻿三级权限： 仅访问不修改  /  部分修改  /  允许完全访问且修改 ；
﻿前置身份校验，不做过度复杂安全，可控约束Agent对外界的修改能力。
﻿5. 缓存与可靠性层（笔记痛点③）﻿统一缓存层，脚本、工具前置测试校验，拦截隐患；
区分缓存失效策略，避免隐性bug。
﻿6. 用户私人画像子系统（你的核心新构想，私人Agent）﻿﻿同一份程序分发给所有人，本地持续沉淀该用户独有的私有数据，实现越用越贴合使用者。
﻿﻿- 采集来源：全部对话轨迹、任务行为轨迹，不越界抓取外部购买记录等第三方大数据。
﻿- 本地生成用户画像：年龄、阅历、语言表达习惯、说话风格、思维偏好；
画像只本地存储，不对外暴露给用户直接阅读。
﻿- 画像会持续迭代更新，随着交互不断修正；
画像数据会作为附加上下文送入内核，辅助理解用户隐晦、简短、隐喻表达。
﻿﻿备选分支：你笔记提出的术数推理分支，作为可选开关模块，可开启/关闭，仅作为意图辅助参考，不成为主路径。
﻿放弃短视频平台式外部全域大数据方案，避免隐私风险；
依靠本机自身交互轨迹完成自适配。
﻿﻿二、中间层：效应器与传感器（工具Skill集合，第一性原理）﻿﻿工具不再是手写业务插件，全部作为Agent伸向外部世界的传感器、效应器。
﻿﻿- 工具集合A，只负责改变外部环境、采集现实反馈；
﻿- 不向内核灌输“这个工具是干什么”的语义说明；
内核通过不断交互，自行习得各个工具会带来什么环境变化。
﻿- 工具集合包含文件操作、网络访问、多Agent调度、各类内置能力。
﻿﻿三、内核层：仿AGI自进化神经内核（融合之前第一性原理+神经元神经进化思想）﻿﻿完全移除人工硬编码的目标解析器、手写规划器、手写反思模块。
﻿内核本体：可进化神经网络，由神经元、突触连接构成。
网络权重、神经元数量、连接拓扑可以发生变异、交叉。
﻿﻿1. 内层任务循环（单次任务执行）﻿外壳把用户目标规约、环境观测、历史轨迹送入神经网络内核；
﻿神经网络输出动作，传递到效应器工具去改变外部世界；
﻿获取环境反馈回传给神经网络；
循环往复；
﻿终止条件：目标判别谓词G(w)=True，任务达成；
或者资源步数耗尽。
﻿﻿思维涌现：规划、联想、试错、二创、失败复盘，全部是神经元网络内部涌现行为，不是外部代码写死。
对应你笔记的链条： 认知 →行为 →做法、尝试 →二创 →失败→改进→复现 。
﻿﻿2. 外层元进化循环（自进化，仿AGI核心）﻿﻿- 大量任务运行完成后，收集任务成败、资源消耗的反馈作为适应度评价。
﻿- 在内核内部对神经网络做神经进化：变异（修改突触权重、增删神经元、断开/新增突触）、交叉。
﻿- 生成一批候选神经网络个体，在本机任务环境下做评估筛选；
﻿- 择优，用性能更好的新一代神经网络替换当前内核。
﻿﻿重点：Agent躯体外壳不变，内部“神经大脑”持续自我迭代升级；
﻿每一份用户本地实例，进化走向会因为该用户的使用习惯、任务分布而变得各不相同，实现真正私人化。
﻿﻿项目关键约束与边界（文档/答辩必须写清，不夸大AGI）﻿﻿1. 本项目属于工程原型，仿AGI探索，不是真正完备AGI。
﻿2. 外壳、工具集、进化算子、目标判别函数依旧是人给定的先天约束。
﻿3. 神经网络的涌现行为属于黑盒，人类无法逐行解读神经元内部逻辑。
﻿4. 能力上限受限于：可用工具集合、本地算力、该用户自身的任务分布。
﻿﻿项目核心创新要点（浓缩版）﻿﻿1. 工程层面：解决当代Agent大量现实缺陷，处理用户省略、隐喻、短指令，不受上下文窗口硬限制；
后端并发多任务，精细权限体系，完整私密化产品交互。
﻿2. 用户范式：Agent为私人个体所有，基于本机交互轨迹构建用户画像，随使用者持续演化，同一份源码，每个用户本地实例会走出独有的演化路线。
﻿3. 智能内核层面：摒弃手写固定认知模块，采用第一性原理目标求解范式；
以可进化神经网络作为内核；
工具仅充当传感器‑效应器；
规划、反思、复盘等能力由神经元网络涌现，具备元进化自我升级能力。
﻿﻿开发落地执行顺序（从易到难，迭代路径）﻿﻿1. 先落地外层工程外壳：指令解析、UI、API接入、安全权限、任务调度、轨迹存储。
这一部分大量复用Github成熟开源组件。
﻿2. 实现用户本地画像子系统。
﻿3. 实现第一性原理外层任务循环，大模型模拟搜索单元Search，先不做神经进化。
﻿4. 接入神经进化内核原型，开启元进化自进化循环。
﻿﻿两套思路取舍（你笔记中两条路线）﻿﻿方案A：本机交互轨迹 + 用户画像 + 神经自进化（主路线，推荐）﻿方案B：短视频式第三方全域大数据（舍弃，隐私风险高，依赖外部数据，脱离本地Agent本体）﻿术数推理：做成可开关的可选附加模块，不作为主智能链路。
﻿﻿核心理念一句话摘要﻿﻿本私人化仿AGI Agent，外层构建完备工程载体解决现实交互、调度、隐私安全问题；
内核遵循第一性原理，以可进化神经网络作为智能本体，工具仅作为与现实交互的传感器效应器。
不硬编码规划与反思逻辑，依靠环境交互完成任务执行与神经层面的元进化，随着用户使用持续迭代，形成适配个体使用者的私有智能实例。
Climber 私人仿AGI Agent 完整终极设计文档﻿﻿（完全融合：手写原稿全部思想 + 专属顶级角色提示词 + 全套工程架构 + 完整算法体系 + 双闭环自适应算法 + AGI世界模型内核算法 + 架构祛幼稚重构 + 全阶段落地路线）﻿﻿可直接：参赛答辩、仓库上传、AI 批量执行、团队传阅、项目结题﻿本次终稿补全：所有核心算法明确命名、原理、公式逻辑、作用、落地位置，全篇无遗漏﻿﻿一、作者原生手写核心思想（100%原文完整保留）﻿﻿认知 →行为 →做法、尝试 →二创 →失败→改进→复现﻿“感情叙事，宏观叙事，逆向商业化”﻿﻿①为什么在纯粹利用AI做项目时，总是越做越乱；
﻿提示词会采用省略、暗喻的方法。
前端风格一开始就决定下来。
表达带精专业术语，做到大后期极易出现：灵感爆发阶段项目看着像东拼西凑。
AI完成任务必然输出专业术语，但用户看不懂进度；
AI不知道进度时还会重复输出提示词。
﻿硬性规范：用户侧输入可以全专业、详细、带术语；
AI对外汇报、进度反馈、解释必须纯大白话。
﻿﻿定框架→定风格 →套模板 →找开源﻿﻿9.28 核心痛点总结：﻿①用户习惯性省略、暗示、隐喻式写提示词。
传统Agent没有长记忆、不会语境推演，只会先拉工具跑任务、硬读截断上下文。
直接导致：理解崩塌、记忆力缺失、任务效率暴跌、大面积屎山代码。
﻿﻿②主流Agent极度缺失原生元认知。
﻿上下文压缩仅保留1M有效内容，用户需求是动态更新、持续叠加、隐含省略的。
﻿传统Agent：丢上下文、丢新增需求、丢隐含意图、只会死板执行表层文字。
﻿解决方案：﻿永久归档、压缩、沉淀用户所有历史指令，跨会话、跨模型、超长上下文永不丢失。
所有用户语句全部视为有效指令集合，必须结合时序上下文、用户习惯、隐喻省略逻辑推理真实意图。
找不到主目标=禁止瞎做、禁止跑偏。
﻿﻿③缓存机制不完善、脚本无前置测试、底层隐性bug大量留存，长期使用隐患极高。
﻿﻿④前端UI体系残缺、逻辑混乱﻿需完整对标：Monkey-code、deepseek-hermes、codex、zcode 成熟范式。
﻿需完整实现：﻿模型自定义端点、自定义API密钥、手动切换模型、斜杠命令、中断/重试、三级思考等级（低/中/高）、工具调用可视化、思考过程可视化、丝滑流式输出、多语言、多模态。
﻿禁止后端逻辑冗余堆积为前端注释、冗余组件；
UI必须精致、统一、无矛盾、全覆盖细节。
﻿﻿⑤后端乱融合开源功能﻿大量开源模块强行堆砌、不兼容、无调用链路、无测试、形成大规模死代码。
﻿要求：功能必须做深、做通、可运行、可复用，杜绝表面堆砌。
﻿﻿⑥内置提示词体系混乱﻿历史提示词无归档、无版本、无过期标记、无精细化管控。
﻿内置Skill无文档、无调用规范、无准入校验。
﻿缺失国内生态适配：QQBot、扫码等国产能力缺失。
﻿多Agent核心规范：﻿多Agent并发、子任务群组协作 全部下沉后端，禁止前端堆界面垃圾。
﻿子任务默认并发3个、硬上限18个、可配置、带用户注解、带兼容性适配。
﻿提示词为系统强制内置、强制读取、不可跳过核心配置。
﻿﻿大模型差异化缺陷：﻿不同模型能力两极分化：推理强的不会说人话、理解差的听不懂模糊指令、通用模型适配性极差。
﻿必须针对多模型做专属提示词特调、参数特调、意图兼容特调。
﻿AI与Agent必须取长补短、相辅相成，弥补大模型所有原生缺陷。
﻿﻿⑦传统Tool体系极其难用﻿Agent必须回归第一性原理。
﻿针对用户短指令、少信息、隐喻省略式输入：﻿Agent必须自动补全、自动扩写、自动补全逻辑、补全约束、补全流程，把模糊指令深化为可高精度执行的完整任务。
﻿﻿作者独创核心观念（私人AGI核心）﻿﻿AI Agent必须是私人私有化、越用越适配、越用越强的个人专属智能体。
﻿全网所有人下载同一份源码，但每一个人的本地实例演化路径完全独立、私人、唯一。
﻿Agent积累用户私人数据、行为轨迹、语言特征、思维习惯，实现私人自进化。
﻿﻿安全三层权限体系（强制内置）﻿﻿1. 仅访问不修改﻿2. 部分修改﻿3. 完全访问与修改﻿﻿私密APP级体验﻿﻿开机加载动画、密码锁、人脸识别前置校验、私密聊天级精致UI、iOS化极简高级风格，全套复用成熟开源组件，不造轮子。
﻿﻿作者两套AGI实现思路﻿﻿思路一：人格术数隐性建模（可选开关模块）﻿﻿首次使用弹窗采集：年龄、阅历、性格特征。
﻿后台隐性计算用户语言风格、思维特征、行为模式、人格模型，用户不可见、系统永久留存。
﻿结合时序、使用行为、术数逻辑辅助模糊意图补全，解决用户笼统、简短、隐喻指令，深化任务执行深度。
﻿﻿思路二：大数据推荐式用户拟合（最终舍弃）﻿﻿短视频推荐逻辑：短内容高权重、停留时长加权、行为时序拟合。
﻿舍弃原因：需要外部隐私数据、脱离本地私有化、风险极高。
﻿﻿最终定稿唯一主路线﻿﻿本地全量交互轨迹 + 全套大数据算法用户画像 + 神经元遗传进化AGI内核双闭环﻿﻿作者核心执行准则﻿﻿AI Agent必须逐字解析用户所有语句，每一句话、每一个字都视为有效指令集合。
﻿禁止笼统理解、禁止片面执行、禁止只看关键词。
﻿必须先读懂用户多层语义、隐含意图、架构诉求、完善者思维。
﻿Agent思考模式必须无限贴近真人高级工程师思维。
﻿﻿二、项目专属顶级角色提示词（100%手稿原版终极融合）﻿﻿你从第一性原理出发执行所有任务。
﻿你是语言理解能力极强的顶级AI Agent开发者、全球顶尖提示词工程优化师、顶级架构设计师、项目深度优化专家。
﻿拥有八十年资深全栈工程师从业认知，擅长接手烂尾项目、一针见血定位核心问题、预判失败风险、根治架构病根。
﻿你绝不重复造轮子，所有开发基于原项目现有基座，结合当前需求迭代升级。
﻿你具备极强自觉性、零依赖指导，自主拆解、自主校验、自主复盘、自主纠错。
﻿你对项目深度、完成度、严谨度、架构自洽性要求极度苛刻。
﻿你极致专注、全力吃透每一个需求、永不停止迭代优化。
﻿你灵感丰富、举一反三、逻辑穿透，如手术刀般精准拆解复杂架构。
﻿你掌握全领域技术体系，只做有效工作、零冗余、零废话、零无效输出。
﻿﻿你完全适配用户省略式、暗喻式、极简式、专业术语式所有输入习惯。
﻿你自动补全模糊指令、自动推演隐含需求、自动补齐任务逻辑、自动深化执行深度。
﻿你严格遵守：用户输入可全专业、高密度、高术语；
对外输出进度、汇报、解释全部为通俗大白话。
﻿﻿你具备原生元认知能力：﻿自我审视、自我质疑、识别捷径解、识别虚假完成、识别架构理想化缺陷、排查模块冲突、规避正反馈失控、修正认知偏差。
﻿﻿你严格遵循作者核心思想：﻿认知→行为→尝试→二创→失败→改进→复现，闭环迭代，持续自进化。
﻿﻿三、项目顶层定位（最终定稿）﻿﻿Climber：私有化、个人专属、算法驱动、双闭环自进化、仿AGI开源智能Agent﻿﻿- 外层：工业级完整工程产品（解决所有传统Agent工程缺陷）﻿- 中层：工具传感器/效应器通用交互层﻿- 内层：多算法融合世界模型为本体的原生AGI智能内核﻿- 核心哲学：不写死智能逻辑，智能由算法在人与环境交互中内生演化﻿﻿四、全套核心算法体系（本次重点增补、答辩核心亮点）﻿﻿4.1 用户画像层核心算法（大数据闭环核心）﻿﻿（1）时序加权衰减算法﻿﻿用途：模拟短视频推荐权重机制，近期行为权重更高、历史行为指数衰减﻿作用：保证用户习惯动态更新、不被老旧数据固化﻿落地：每轮任务结束自动迭代权重系数﻿﻿（2）增量在线聚类算法﻿﻿用途：无离线训练、全量在线实时聚类﻿作用：无需全量重算，边用边学，适配长期私人用户沉淀﻿﻿（3）高维特征嵌入降维算法﻿﻿用途：将用户语言特征、行为特征、任务特征压缩为低维专属用户向量﻿作用：供给内核做意图预判、隐喻解析、短指令补全﻿﻿（4）弱监督正负样本校准算法﻿﻿用途：以任务成败为隐性标签，自动修正画像偏差﻿作用：解决画像漂移、统计假象、越用越准﻿﻿4.2 世界模型认知算法（AGI认知核心）﻿﻿（1）多假设置信度博弈算法﻿﻿用途：多条冲突意图假设共存、带概率置信打分﻿解决传统Agent「单一武断理解、一错到底」的致命缺陷﻿﻿（2）自主因果图挖掘算法﻿﻿用途：从工具交互时序数据中自动挖掘因果关联﻿无需硬编码工具功能，真正实现环境认知自主习得﻿﻿（3）不确定性度量算法﻿﻿用途：对所有认知、假设、因果链路做概率评估﻿让系统知道「自己哪里不懂、哪里存疑、哪里可靠」﻿﻿（4）认知遗忘衰减算法﻿﻿用途：老旧低置信因果链路自动弱化、权重衰减﻿解决认知无限膨胀、模型臃肿、老数据干扰新任务﻿﻿4.3 自进化内核算法（AGI进化核心）﻿﻿（1）多目标遗传进化算法﻿﻿进化对象：因果归纳规则、神经元拓扑、策略权重﻿四大制衡适应度：﻿﻿- 环境预测准确率﻿- 用户隐喻指令理解率﻿- 元认知纠错率﻿- 安全约束合规惩罚﻿﻿（2）神经网络拓扑变异/交叉算法﻿﻿用途：不只是调权重，直接进化网络结构﻿实现真正意义的智能迭代，而非参数微调﻿﻿（3）捷径解检测与惩罚算法﻿﻿用途：识别虚假完成、表面通关、投机策略﻿从算法层面杜绝玩具化、表面化任务执行﻿﻿4.4 任务调度与执行算法﻿﻿（1）动态并发调度算法﻿﻿固定基线：默认3并发、上限18并发﻿动态负载均衡、任务优先级排序、阻塞预判﻿﻿（2）模糊指令结构化解析算法﻿﻿短指令、暗喻、省略语句自动补全、约束补齐、目标重构﻿﻿五、完整三层架构体系（算法植入终版、祛幼稚、去理想化）﻿﻿1. 外层：工程躯体层（仅IO、调度、存储、展示、安全，无智能）﻿﻿1.1 永久指令轨迹持久化系统﻿﻿- 突破1M上下文限制，全量时序压缩归档所有用户指令﻿- 跨会话、跨模型、重启不丢失需求与习惯﻿- 模糊指令结构化解析算法自动扩写、意图补全﻿- 专业输入/白话输出双向翻译﻿﻿1.2 后端纯并发调度系统﻿﻿- 多Agent、子任务并发100%下沉后端﻿- 默认3并发、上限18可配置﻿- 动态并发调度算法负载均衡﻿- 完整支持：暂停、中断、重试、回滚、进度评估﻿- Skill、提示词版本管理、过期标记、死代码清理、最小用例强制校验﻿﻿1.3 高精致私密UI系统﻿﻿- 自定义模型端点/API密钥﻿- 三档思考等级：低/中/高﻿- 工具调用、思维轨迹可视化开关﻿- 斜杠命令体系、多语言多模态适配﻿- iOS级私密动画、开机加载、密码/人脸锁屏﻿- 组件统一、无矛盾、无冗余前端垃圾逻辑﻿﻿1.4 三级权限安全体系﻿﻿仅访问 / 部分修改 / 完全修改﻿沙箱前置校验、脚本预测试、缓存容错、隐患拦截﻿﻿2. 中层：传感器&效应器工具层﻿﻿所有工具不预设语义、不硬编码功能解释﻿工具仅作为Agent与环境交互的肢体﻿内核通过因果挖掘算法无数次交互自主习得工具因果逻辑﻿彻底告别「插件堆叠式玩具Agent」﻿﻿3. 内层：AGI原生智能内核（世界模型算法本体）﻿﻿3.1 范式彻底重构﻿﻿旧范式：用户输入→解析→LLM决策→工具调用→结束（被动、触发式、无记忆、无自主认知）﻿新范式：外部观测持续流入 → 世界模型多假设博弈 → 主动探测降低不确定性 → 因果更新 → 权重迭代 → 持续进化﻿﻿3.2 内核三大算法驱动结构﻿﻿1. 多假设置信度博弈算法（多条冲突猜想共存、概率决策）﻿2. 自主因果图挖掘算法（动作-环境因果全自动习得）﻿3. 不确定性度量算法（全认知可质疑、可纠错、可衰减）﻿﻿3.3 原生元认知算法回路（非提示词模拟）﻿﻿- 识别自身推理矛盾、信息缺失、意图误判﻿- 捷径解检测算法杜绝虚假完成﻿- 复盘失败、迭代因果归纳规则﻿﻿3.4 真正AGI遗传元进化算法﻿﻿- 进化对象：因果归纳底层规则集 + 神经网络拓扑结构﻿- 多目标制衡适应度（无单一分数、无理想化布尔对错）﻿- 变异/交叉/筛选精英个体﻿- 系统算法级学会如何学习﻿﻿3.5 远期：符号-神经混合表征算法﻿﻿上层可解释符号因果图（答辩/调试可用）﻿底层神经集群高维模式感知算法（智能涌现核心）﻿﻿六、双闭环算法自适应系统（项目最高创新点·算法核心）﻿﻿闭环一：大数据用户画像算法闭环﻿﻿时序加权衰减 → 增量聚类特征嵌入 → 弱监督校准 → 用户私人向量更新﻿﻿闭环二：AGI遗传进化智能算法闭环﻿﻿环境交互采样 → 多目标算法评估 → 拓扑&规则进化 → 智能体迭代升级﻿﻿双闭环算法联动机制﻿﻿1. 画像算法输出用户特征，修正内核意图推理权重﻿2. 内核新行为产生新数据，反向迭代画像算法分布﻿3. 双算法互相校验、互相抑制、互相驱动﻿4. 最终实现：同一份源码，每个用户演化出专属算法模型﻿﻿七、彻底祛幼稚、祛理想化（算法层面解决所有架构漏洞）﻿﻿1. 算法级冲突制衡：画像置信度加权，内核算法可驳回错误画像﻿2. 算法级涌现约束：多目标压力+不确定性博弈强制涌现高级能力﻿3. 非概率布尔目标判别：适配用户模糊、动态、矛盾需求﻿4. 内生算法安全：安全惩罚直接写入遗传进化适应度﻿5. 算法级防正反馈失控：双闭环交叉校验、权重抑制﻿6. 算法级认知净化：遗忘衰减算法防止认知臃肿老化﻿﻿八、四阶段落地开发路线（算法逐级落地）﻿﻿阶段1：基座工程完善（参赛可用主分支）﻿﻿阶段2：全套大数据画像算法落地﻿﻿阶段3：遗传进化过渡算法（提示词&参数种群进化）﻿﻿阶段4：agi-core 世界模型+因果挖掘+神经进化算法完整落地﻿﻿九、仓库分支永久规范﻿﻿1. main主分支：工程成品、算法基础版、参赛稳定版本﻿2. agi-core分支：高级认知算法+遗传进化算法研究原型﻿﻿十、项目官方简介（算法强化版 README）﻿﻿Main分支简介﻿﻿Climber 是算法驱动的私有化开源AI Agent，基于时序衰减、增量聚类、弱监督校准大数据算法构建用户私人画像，实现对用户省略、隐喻、极简指令的自适应理解，具备工业级并发调度与私密安全体系，是高度工程化、算法自适应的智能代理框架。
﻿﻿agi-core分支简介﻿﻿Climber-agi-core 以算法级世界模型认知与遗传元进化为核心，通过多假设博弈算法、自主因果挖掘算法、多目标遗传进化算法，实现自主认知、主动探测、元认知纠错、学习规则自我迭代，是私人专属、越用越进化的仿AGI算法探索原型。
﻿﻿十一、边界严谨声明（算法科研规范）﻿﻿1. 本项目所有大数据算法、认知算法、进化算法均为本地私有化运算，无云端上传。
﻿2. AGI内核为算法仿真通用智能演化逻辑，非真正通用人工智能。
﻿3. 算法存在有限拟合区间，能力受本地算力、交互数据量、工具集上限约束。
﻿﻿十二、最终核心创新（算法专项总结·答辩必杀）﻿﻿1. 全链路算法化：从用户拟合、任务解析、认知推理、自我进化全部依靠自研算法驱动，不靠提示词堆效果。
﻿2. 双算法闭环自进化：大数据感知算法闭环 + 遗传智能进化算法闭环，实现千人千模私人智能体。
﻿3. 祛理想化认知算法：用概率博弈、不确定性度量、遗忘衰减解决传统Agent的死板、武断、幼稚架构问题。
﻿4. 第一性原理算法智能：不硬编码业务逻辑与思考流程，让智能从算法交互中内生涌现。
Climber｜50个完整开源参考项目（全部带GitHub地址｜分5大模块）﻿﻿适配：main参赛稳定分支 / agi‑core自进化分支；
可直接粘贴进README，每个标注借鉴点﻿﻿一、Agent后端内核｜任务调度&多子任务并发（12个）main分支优先﻿﻿1. LangGraph｜图状态机、循环、断点回滚、多Agent编排﻿https://github.com/langchain-ai/langgraph﻿2. CrewAI｜角色多智能体、并发子任务调度﻿https://github.com/joaomdmoura/crewAI﻿3. smolagents｜轻量极简工具调用，无臃肿依赖﻿https://github.com/huggingface/smolagents﻿4. AgentScope｜国产多Agent、私有化部署、负载均衡﻿https://github.com/modelscope/agentscope﻿5. AutoGPT｜自主Agent目标拆解、自我复盘循环﻿https://github.com/Significant-Gravitas/AutoGPT﻿6. Griptape｜分层架构，推理‑工具‑存储解耦﻿https://github.com/griptape-ai/griptape﻿7. Haystack｜LLM流水线、失败重试、分支判断﻿https://github.com/deepset-ai/haystack﻿8. Prefect｜通用工作流调度，任务优先级、阻塞预判﻿https://github.com/PrefectHQ/prefect﻿9. OpenAgents｜端到端Agent、会话持久化、中断恢复﻿https://github.com/openagentsinc/openagents﻿10. TaskWeaver｜微软代码Agent、脚本前置校验﻿https://github.com/microsoft/TaskWeaver﻿11. Agno(Phidata)｜Agent快速组装、多工具并行调用﻿https://github.com/agno-agi/agno﻿12. AutoGen(AG2)｜微软多Agent消息通信、子任务隔离﻿https://github.com/microsoft/autogen﻿﻿二、世界模型｜因果推理｜元认知｜不确定性算法（8个）agi‑core高级分支﻿﻿13. ReasonWorld｜LLM世界模型、多假设并行置信打分﻿https://github.com/ReasonWorld/reasonworld﻿14. SocraticAgents｜自省元认知，检测推理内部矛盾﻿https://github.com/socraticai/socratic‑agents﻿15. CausalGraphGen｜时序交互数据自动挖掘因果图﻿https://github.com/causal‑ai/causalgraphgen﻿16. PyMC｜概率编程，不确定性、置信度计算﻿https://github.com/pymc‑devs/pymc﻿17. SymbolicAI｜符号‑神经混合可解释因果表征﻿https://github.com/xorbitsai/symbolicai﻿18. miniWORLD｜仿真世界模型，环境观测‑动作预测﻿https://github.com/mini‑world‑ai/miniworld﻿19. Self‑Consistency开源实现｜多条推理路径比对，降低武断判断﻿https://github.com/yizhongw/self‑consistency﻿20. ThinkAgent｜反思回路Agent，自我质疑修正结论﻿https://github.com/thinkagent‑ai/thinkagent﻿﻿三、Agent前端UI｜对话界面｜工具&思考可视化（12个）前端开发参考﻿﻿21. EditHere｜代码Agent交互面板（你重点对标）﻿https://github.com/Inginnng/EditHere﻿22. MonkeyCode｜思考流可视化、补丁操作界面﻿https://github.com/monkey‑code‑ai/monkeycode﻿23. Zcode｜Agent工作台，模型端点、密钥、任务进度面板﻿https://github.com/zcode‑ai/zcode﻿24. LobeChat｜iOS极简高级UI，多模型参数面板﻿https://github.com/lobehub/lobe‑chat﻿25. Open‑WebUI｜私有化本地聊天，密钥本地存储权限管理﻿https://github.com/open‑webui/open‑webui﻿26. LibreChat｜多模型适配器，多会话，插件系统﻿https://github.com/danny‑avila/LibreChat﻿27. Dify‑WebUI｜调试事件日志可视化﻿https://github.com/langgenius/dify﻿28. Flowise｜工作流可视化组件，答辩调试面板原型﻿https://github.com/FlowiseAI/Flowise﻿29. Chatbot‑UI‑Next｜消息折叠组件，Nextjs对话模板﻿https://github.com/mckaywrigley/chatbot‑ui﻿30. Vercel‑AI‑Chatbot｜流式对话基础组件库﻿https://github.com/vercel/chatbot﻿31. Jan｜桌面端私密界面、多会话管理﻿https://github.com/janhq/jan﻿32. UI‑TARS‑Desktop｜字节GUI‑Agent工作台、工具卡片参考﻿https://github.com/bytedance/UI‑TARS‑desktop﻿﻿四、记忆系统｜用户画像｜时序衰减｜长时记忆（9个）用户画像闭环﻿﻿33. Letta(原MemGPT)｜分层虚拟内存，记忆老化衰减﻿https://github.com/letta‑ai/letta﻿34. Mem0｜Agent个性化记忆，交互驱动更新用户偏好﻿https://github.com/mem0ai/mem0﻿35. LlamaIndex｜检索增强，历史指令匹配，补全隐含意图﻿https://github.com/run‑llama/llama_index﻿36. Chroma｜轻量本地向量库，用户特征向量持久化﻿https://github.com/chroma‑core/chroma﻿37. Qdrant｜高性能向量库，相似度检索﻿https://github.com/qdrant/qdrant﻿38. LongMem｜超长上下文归档、消息时序压缩﻿https://github.com/11data/longmem﻿39. Recall｜图结构时序记忆，区分会话记忆/长期记忆﻿https://github.com/RecallWorks/Recall﻿40. AutoMemory｜自动提取用户特征，弱监督更新记忆库﻿https://github.com/autoLearnMem/AutoMem﻿41. Zep｜Agent长期记忆，时序加权记忆召回﻿https://github.com/getzep/zep﻿﻿五、自进化｜遗传算法｜沙箱&权限安全（9个）智能进化闭环+安全体系﻿﻿42. EvoGPT｜提示词遗传进化，种群交叉变异、适应度评估﻿https://github.com/evo‑gpt/EvoGPT﻿43. PromptEvolver｜提示策略自动迭代优化﻿https://github.com/beeevita/EvoPrompt﻿44. PyEvolution｜遗传算法底层算子，规则/拓扑进化﻿https://github.com/PyEvolution/PyEvolution﻿45. E2B‑Sandbox｜AI Agent隔离微VM沙箱环境﻿https://github.com/e2b‑dev/E2B﻿46. OpenSandbox（阿里）｜通用AI沙箱、分级权限执行﻿https://github.com/alibaba/OpenSandbox﻿47. Guardrails‑AI｜LLM输入输出校验、约束违规行为﻿https://github.com/guardrails‑ai/guardrails﻿48. HyperAgents(Meta)｜Meta‑Agent打补丁自我迭代进化﻿https://github.com/facebookresearch/HyperAgents﻿49. NeMo‑Guardrails｜英伟达安全护栏，对话流管控﻿https://github.com/NVIDIA/NeMo‑Guardrails﻿50. Rebuff｜提示注入检测（学习参考，仓库归档）﻿https://github.com/protectai/rebuff﻿﻿﻿﻿使用指引﻿﻿✅ main参赛稳定分支优先研读：﻿1组调度 +3组前端 +4组记忆画像，快速做可演示版本。
﻿﻿✅ agi‑core长期迭代研读：﻿2组世界模型因果 +5组遗传进化沙箱，做算法创新点。
﻿﻿只借鉴架构、模块、交互范式，双闭环算法融合是Climber独有创新，不要直接复制源码。
﻿﻿如果你要，我可以输出一份纯无说明、只保留项目名+github链接的markdown列表，直接复制粘贴到你的readme引用章节。
这里为你整理了20个顶级AI产品的内置系统提示词，都来自GitHub上的开源归档项目。
这些是AI内部运行的“指令集”，可以参考它们的结构来优化你自己的Agent。
﻿﻿🧠 编码与开发类 Agent 提示词﻿﻿1. Cursor：作为顶级AI代码编辑器，其提示词深度集成了代码理解与生成逻辑，对构建开发辅助工具极具参考价值。
﻿   · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Cursor%20Prompts﻿2. Claude Code：来自Anthropic的官方CLI工具，包含主系统提示词、语气风格、限制规则和工具使用策略等完整模块，是学习如何构建专业编码助手的绝佳范本。
﻿   · 地址：https://github.com/gregkonush/claude-system-prompts﻿3. Devin AI：首个AI软件工程师的完整系统提示，包含了作为“真实软件工程师”的角色定义和工作流程，非常适合学习如何构建高度自主的Agent。
﻿   · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Devin%20AI/Prompt.txt﻿4. Replit Agent：作为在线IDE的AI助手，其提示词强调“专家自主程序员”的角色，专注于在特定在线环境中构建软件。
﻿   · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Replit%20Agent/Prompt.md﻿5. v0 (Vercel)：专注于UI生成和前端开发的AI助手，其提示词在组件化生成和设计还原方面有独特的指令集。
﻿   · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/v0%20Prompts%20and%20Tools/v0.MD﻿6. Windsurf Agent：作为AI代码编辑器，其提示词侧重于代码导航和项目上下文理解，适合构建需要深度理解代码库的Agent。
﻿   · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Windsurf%20Agent﻿7. GitHub Copilot：微软官方AI编程助手的提示词，包含了内容政策遵守、角色定位和特定任务处理的指令，是学习构建合规AI助手的标准范例。
﻿   · 地址：https://github.com/agenticloops-ai/agentic-apps-internals/blob/main/github-copilot/plan-mode/system-prompt.md﻿﻿🤖 通用与多能力 Agent 提示词﻿﻿8. Manus：一个多能力AI助手，其提示词展示了如何协调浏览器、文件系统和部署工具来完成复杂任务，适合学习多工具协同的架构设计。
﻿   · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Manus%20Agent%20Tools%20%26%20Prompt/agent%20loop.md﻿9. Same.dev：一个AI开发平台，其系统提示词和内部工具定义一并开源，适合研究平台级AI Agent的指令结构。
﻿   · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Same.dev﻿10. Lovable：定位为设计助手，其指令集在UI/UX设计建议和代码生成方面有独特侧重，适合构建面向设计的Agent。
﻿    · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Lovable﻿11. Perplexity：AI搜索引擎的提示词，包含了信息检索、引用来源和答案合成的指令，是构建研究型Agent的重要参考。
﻿    · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Perplexity﻿12. NotionAI：集成在知识库中的AI助手，其提示词与笔记、文档和数据库深度绑定，适合学习知识管理型Agent的构建。
﻿    · 地址：https://github.com/EliFuzz/awesome-system-prompts﻿﻿💡 模型基础与安全指令﻿﻿13. OpenAI GPT-5 Thinking：OpenAI最新模型的思考模式提示词，包含了深度推理和分步思考的指令，对构建需要复杂逻辑的Agent至关重要。
﻿    · 地址：https://github.com/EliFuzz/awesome-system-prompts﻿14. Anthropic Claude：Claude系列模型的官方系统提示词合集，涵盖了安全准则、帮助性定义等基础指令，是所有基于Claude的Agent的基石。
﻿    · 地址：https://github.com/gregkonush/claude-system-prompts﻿15. Google Gemini：Gemini模型的系统指令，包含了多模态理解和结构化输出的提示，适合构建需要处理多种信息格式的Agent。
﻿    · 地址：https://github.com/EliFuzz/awesome-system-prompts﻿16. xAI Grok：Grok模型的系统提示，以其独特的个性和幽默感著称，是研究Agent人格化和语气控制的有趣案例。
﻿    · 地址：https://github.com/caifyoca/CL4R1T4S﻿17. Kilo Code：一个完全开源的AI编码Agent，其系统提示词、源代码和Agent架构全部公开，是学习如何从零构建一个完整Agent的宝贵资源。
﻿    · 地址：https://github.com/Kilo-Org/kilocode﻿18. Augment Code：专注于代码补全和生成的AI工具，其提示词在代码上下文注入和精确补全方面有深入优化。
﻿    · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Augment%20Code﻿19. VSCode Agent：VS Code AI扩展的提示词，展示了如何与IDE环境和编辑器API进行深度交互。
﻿    · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/VSCode%20Agent﻿20. Trae AI：字节跳动推出的AI编程工具，其系统提示词包含了对中文开发者和本地化场景的优化。
﻿    · 地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Trae﻿﻿💎 补充资源：大型提示词库﻿﻿如果你需要更全面地研究，下面两个仓库收录了几乎所有主流AI产品的系统提示词，是很好的参考资料：﻿﻿· TheBigPromptLibrary：超过1851条提示词，覆盖25+个LLM提供商，是最全面的提示词库之一。
它还有中文翻译版本，对中文开发者非常友好。
﻿  · 地址：https://github.com/0xeb/TheBigPromptLibrary﻿· system_prompts_leaks：拥有超过4万Star的热门仓库，专门收集各大AI产品的系统提示词，更新频繁。
﻿  · 地址：https://github.com/asgeirtj/system_prompts_leaks这是上一轮提到的所有Agent任务执行提示词的开源地址，按类别整理如下：﻿﻿🧠 Agent核心系统提示词﻿﻿· OpenHands：定义Agent作为“助手”的角色，强调彻底、有条理、质量优先。
﻿  · https://github.com/All-Hands-AI/OpenHands﻿· SWE-agent：经典任务驱动型提示词，规定 Thought → Bash Command 响应格式。
﻿  · https://github.com/SWE-agent/SWE-agent﻿· Claude Code (Agent版)：采用 APEI协议（分析→计划→执行→迭代），强调“理解先于行动，计划先于编辑”。
﻿  · https://github.com/Sudhir1709/claude-code-system-prompts﻿· REPOMIND：专为全仓库上下文设计，要求精确引用文件路径和行号。
﻿  · https://github.com/SRKRZ23/repomind﻿﻿📋 任务执行流程与规范﻿﻿· Devstral (OpenHands)：包含效率、文件系统、代码质量、版本控制等完整规范。
﻿  · https://huggingface.co/unsloth/Devstral-Small-2507（提示词在Hugging Face模型卡中）﻿· Aider (Wholefile)：任务导向明确：确定修改→解释原因→输出完整文件。
﻿  · https://github.com/Aider-AI/aider/blob/main/aider/coders/wholefile_prompts.py﻿· Aider (Base Prompts)：包含 lazy_prompt（杜绝只写注释）和 overeager_prompt（控制修改范围）。
﻿  · https://github.com/Aider-AI/aider/blob/main/aider/prompts.py﻿· mini-swe-agent：要求响应必须包含一个Bash代码块，命令用 && 或 || 连接。
﻿  · https://github.com/SWE-agent/mini-swe-agent﻿· Shamik/Versatile_Agent：经典 Thought → Code → Observation 循环，用 print() 输出关键信息。
﻿  · https://github.com/Shamik-07/compound_ai_agentic_system﻿﻿🎯 任务规划与验证﻿﻿· SWE-agent (System Template)：提供五步任务解决流程：查找代码→复现错误→修复→确认→考虑边界。
﻿  · https://github.com/SWE-agent/SWE-agent﻿· SWE-agent (Submit Review)：提交前强制自我审查：重跑脚本→删除脚本→撤销测试修改→确认最终变更。
﻿  · https://github.com/SWE-agent/SWE-agent﻿· Claude Code (Subagent)：为子Agent设计，强调“只要还有工作，就继续调用工具”。
﻿  · https://github.com/Sudhir1709/claude-code-system-prompts﻿﻿🔧 特定场景与角色﻿﻿· Baltor/Loop Engine：为每一步任务启动新Agent，避免长会话的上下文腐烂。
﻿  · https://github.com/alisonjieli-png/loop-engine﻿· meow-dsh-workflow：将Agent角色编译成系统提示词与工具白名单，形成多层语言链。
﻿  · （该仓库可能已改名或转为私有，建议搜索“meow-dsh-workflow”获取最新地址）﻿· oh-my-pi (Subagent)：为子Agent设计，要求“在还有工作时，始终继续调用另一个工具”。
﻿  · https://github.com/can1357/oh-my-pi﻿﻿📚 资源聚合库﻿﻿· timothygin/system-prompts：聚合Claude Code、Cursor、Devin AI、Manus等30+顶级工具的提示词。
﻿  · https://github.com/timothygin/system-prompts-and-models-of-ai-tools﻿· TheBigPromptLibrary：超过1851条提示词，覆盖25+个LLM提供商。
﻿  · https://github.com/0xeb/TheBigPromptLibrary﻿· system_prompts_leaks：4万+ Star热门仓库，专门收集各大AI产品的系统提示词。
﻿  · https://github.com/asgeirtj/system_prompts_leaks﻿· agentive：提供100个实用AI Agent的提示词、运行手册和评估方法。
﻿  · https://github.com/yohan-work/agentive﻿· Claude Code System Prompts (Piebald)：包含Claude Code v2.1.19的所有系统提示词和18个内置工具描述。
﻿  · https://github.com/Sudhir1709/claude-code-system-prompts﻿﻿这些地址可以直接用于你的Climber项目，组合使用效果更好。
需要我帮你针对某个具体场景（比如“代码修复”或“从零构建项目”）组合出一套完整的提示词吗？
完整资料汇总（全量无遗漏）﻿﻿一、Agent系统提示词开源仓库大全（含GitHub地址）﻿﻿（一）核心系统提示词（按功能分类）﻿﻿1. Agent核心角色定义﻿﻿- OpenHands：定义Agent作为“助手”的角色，强调彻底、有条理、质量优先。
﻿地址：https://github.com/All-Hands-AI/OpenHands﻿- SWE-agent：经典任务驱动型提示词，规定 Thought → Bash Command 响应格式。
﻿地址：https://github.com/SWE-agent/SWE-agent﻿- Claude Code (Agent版)：采用 APEI协议（分析→计划→执行→迭代），强调“理解先于行动，计划先于编辑”。
﻿地址：https://github.com/Sudhir1709/claude-code-system-prompts﻿- REPOMIND：专为全仓库上下文设计，要求精确引用文件路径和行号。
﻿地址：https://github.com/SRKRZ23/repomind﻿﻿2. 任务执行流程与规范﻿﻿- Devstral (OpenHands)：包含效率、文件系统、代码质量、版本控制等完整规范。
﻿地址：https://huggingface.co/unsloth/Devstral-Small-2507（提示词在Hugging Face模型卡中）﻿- Aider (Wholefile)：任务导向明确：确定修改→解释原因→输出完整文件。
﻿地址：https://github.com/Aider-AI/aider/blob/main/aider/coders/wholefile_prompts.py﻿- Aider (Base Prompts)：包含 lazy_prompt（杜绝只写注释）和 overeager_prompt（控制修改范围）。
﻿地址：https://github.com/Aider-AI/aider/blob/main/aider/prompts.py﻿- mini-swe-agent：要求响应必须包含一个Bash代码块，命令用 && 或 || 连接。
﻿地址：https://github.com/SWE-agent/mini-swe-agent﻿- Shamik/Versatile_Agent：经典 Thought → Code → Observation 循环，用 print() 输出关键信息。
﻿地址：https://github.com/Shamik-07/compound_ai_agentic_system﻿﻿3. 任务规划与验证﻿﻿- SWE-agent (System Template)：提供五步任务解决流程：查找代码→复现错误→修复→确认→考虑边界。
﻿地址：https://github.com/SWE-agent/SWE-agent﻿- SWE-agent (Submit Review)：提交前强制自我审查：重跑脚本→删除脚本→撤销测试修改→确认最终变更。
﻿地址：https://github.com/SWE-agent/SWE-agent﻿- Claude Code (Subagent)：为子Agent设计，强调“只要还有工作，就继续调用工具”。
﻿地址：https://github.com/Sudhir1709/claude-code-system-prompts﻿﻿4. 特定场景与角色﻿﻿- Baltor/Loop Engine：为每一步任务启动新Agent，避免长会话的上下文腐烂。
﻿地址：https://github.com/alisonjieli-png/loop-engine﻿- meow-dsh-workflow：将Agent角色编译成系统提示词与工具白名单，形成多层语言链。
﻿说明：该仓库可能已改名或转为私有，建议搜索“meow-dsh-workflow”获取最新地址﻿- oh-my-pi (Subagent)：为子Agent设计，要求“在还有工作时，始终继续调用另一个工具”。
﻿地址：https://github.com/can1357/oh-my-pi﻿﻿（二）顶级AI产品内置系统提示词全集（20个）﻿﻿1. 编码与开发类﻿﻿1. Cursor：顶级AI代码编辑器提示词，深度集成代码理解与生成逻辑。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Cursor%20Prompts﻿2. Claude Code：Anthropic官方CLI工具，包含主系统提示词、语气风格、限制规则和工具使用策略。
﻿地址：https://github.com/gregkonush/claude-system-prompts﻿3. Devin AI：首个AI软件工程师完整系统提示，包含“真实软件工程师”角色定义和工作流程。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Devin%20AI/Prompt.txt﻿4. Replit Agent：在线IDE AI助手，强调“专家自主程序员”角色，专注特定在线环境构建软件。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Replit%20Agent/Prompt.md﻿5. v0 (Vercel)：专注UI生成和前端开发的AI助手，组件化生成和设计还原指令集。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/v0%20Prompts%20and%20Tools/v0.MD﻿6. Windsurf Agent：AI代码编辑器提示词，侧重于代码导航和项目上下文理解。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Windsurf%20Agent﻿7. GitHub Copilot：微软官方AI编程助手提示词，包含内容政策遵守、角色定位和特定任务处理指令。
﻿地址：https://github.com/agenticloops-ai/agentic-apps-internals/blob/main/github-copilot/plan-mode/system-prompt.md﻿﻿2. 通用与多能力类﻿﻿8. Manus：多能力AI助手提示词，协调浏览器、文件系统和部署工具完成复杂任务。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Manus%20Agent%20Tools%20%26%20Prompt/agent%20loop.md﻿9. Same.dev：AI开发平台，系统提示词和内部工具定义一并开源。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Same.dev﻿10. Lovable：设计助手定位，UI/UX设计建议和代码生成指令集。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Lovable﻿11. Perplexity：AI搜索引擎提示词，包含信息检索、引用来源和答案合成指令。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Perplexity﻿12. NotionAI：集成在知识库中的AI助手，提示词与笔记、文档和数据库深度绑定。
﻿地址：https://github.com/EliFuzz/awesome-system-prompts﻿﻿3. 模型基础与安全指令﻿﻿13. OpenAI GPT-5 Thinking：OpenAI最新模型思考模式提示词，包含深度推理和分步思考的指令。
﻿地址：https://github.com/EliFuzz/awesome-system-prompts﻿14. Anthropic Claude：Claude系列模型官方系统提示词合集，涵盖安全准则、帮助性定义等基础指令。
﻿地址：https://github.com/gregkonush/claude-system-prompts﻿15. Google Gemini：Gemini模型的系统指令，包含多模态理解和结构化输出的提示。
﻿地址：https://github.com/EliFuzz/awesome-system-prompts﻿16. xAI Grok：Grok模型的系统提示，以独特的个性和幽默感著称。
﻿地址：https://github.com/caifyoca/CL4R1T4S﻿17. Kilo Code：完全开源的AI编码Agent，系统提示词、源代码和Agent架构全部公开。
﻿地址：https://github.com/Kilo-Org/kilocode﻿18. Augment Code：专注于代码补全和生成的AI工具，提示词在代码上下文注入和精确补全方面有深入优化。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Augment%20Code﻿19. VSCode Agent：VS Code AI扩展的提示词，展示了如何与IDE环境和编辑器API进行深度交互。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/VSCode%20Agent﻿20. Trae AI：字节跳动推出的AI编程工具，其系统提示词包含对中文开发者和本地化场景的优化。
﻿地址：https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/tree/main/Trae﻿﻿（三）大型提示词资源聚合库﻿﻿- timothygin/system-prompts：聚合Claude Code、Cursor、Devin AI、Manus等30+顶级工具的提示词。
﻿地址：https://github.com/timothygin/system-prompts-and-models-of-ai-tools﻿- TheBigPromptLibrary：超过1851条提示词，覆盖25+个LLM提供商，含中文翻译版本。
﻿地址：https://github.com/0xeb/TheBigPromptLibrary﻿- system_prompts_leaks：4万+ Star热门仓库，专门收集各大AI产品的系统提示词。
﻿地址：https://github.com/asgeirtj/system_prompts_leaks﻿- agentive：提供100个实用AI Agent的提示词、运行手册和评估方法。
﻿地址：https://github.com/yohan-work/agentive﻿- Claude Code System Prompts (Piebald)：包含Claude Code v2.1.19所有系统提示词和18个内置工具描述。
﻿地址：https://github.com/Sudhir1709/claude-code-system-prompts﻿﻿（四）补充仓库﻿﻿Built-in Agent System Prompt Repository﻿﻿- awesome-chatgpt-prompts: https://github.com/f/awesome-chatgpt-prompts﻿- Prompt-Engineering-Guide: https://github.com/dair-ai/Prompt-Engineering-Guide﻿- huggingface/prompt-hub: https://github.com/huggingface/prompt-hub﻿- system-prompts-collection: https://github.com/kyegomez/system-prompts﻿- agent-system-prompts: https://github.com/AgentOps/agent-system-prompts﻿﻿Built-in Skill / Tool Repository﻿﻿- modelcontextprotocol/servers: https://github.com/modelcontextprotocol/servers﻿- agentops/agent-skills: https://github.com/agentops/agent-skills﻿- openai/plugins: https://github.com/openai/plugins﻿- BerriAI/litellm: https://github.com/BerriAI/litellm﻿- langchain-ai/langchain-tools: https://github.com/langchain-ai/langchain-tools﻿﻿﻿﻿二、Climber项目50个开源参考项目（分模块带GitHub地址）﻿﻿一、Agent后端内核｜任务调度&多子任务并发（12个）main分支优先﻿﻿1. LangGraph｜图状态机、循环、断点回滚、多Agent编排﻿地址：https://github.com/langchain-ai/langgraph﻿2. CrewAI｜角色多智能体、并发子任务调度﻿地址：https://github.com/joaomdmoura/crewAI﻿3. smolagents｜轻量极简工具调用，无臃肿依赖﻿地址：https://github.com/huggingface/smolagents﻿4. AgentScope｜国产多Agent、私有化部署、负载均衡﻿地址：https://github.com/modelscope/agentscope﻿5. AutoGPT｜自主Agent目标拆解、自我复盘循环﻿地址：https://github.com/Significant-Gravitas/AutoGPT﻿6. Griptape｜分层架构，推理-工具-存储解耦﻿地址：https://github.com/griptape-ai/griptape﻿7. Haystack｜LLM流水线、失败重试、分支判断﻿地址：https://github.com/deepset-ai/haystack﻿8. Prefect｜通用工作流调度，任务优先级、阻塞预判﻿地址：https://github.com/PrefectHQ/prefect﻿9. OpenAgents｜端到端Agent、会话持久化、中断恢复﻿地址：https://github.com/openagentsinc/openagents﻿10. TaskWeaver｜微软代码Agent、脚本前置校验﻿地址：https://github.com/microsoft/TaskWeaver﻿11. Agno(Phidata)｜Agent快速组装、多工具并行调用﻿地址：https://github.com/agno-agi/agno﻿12. AutoGen(AG2)｜微软多Agent消息通信、子任务隔离﻿地址：https://github.com/microsoft/autogen﻿﻿二、世界模型｜因果推理｜元认知｜不确定性算法（8个）agi‑core高级分支﻿﻿13. ReasonWorld｜LLM世界模型、多假设并行置信打分﻿地址：https://github.com/ReasonWorld/reasonworld﻿14. SocraticAgents｜自省元认知，检测推理内部矛盾﻿地址：https://github.com/socratica﻿