# mattpocock/skills 深挖（防瞎写代码的编码工程 Skill 库）

> 核验日期：2026-10-01。结论仅来自本会话实时抓取的公开仓库内容（api.github.com 元数据、raw.githubusercontent.com 原文、git clone 浅克隆全量核验），未做任何猜测性补写。

## 一、仓库状态/许可证/可达性实证

- 地址：`https://github.com/mattpocock/skills`。
- 可达性：`GET https://api.github.com/repos/mattpocock/skills` 返回 200。实证字段：`id: 1148788086`、`full_name: "mattpocock/skills"`、`private: false`、`default_branch: "main"`、`created_at: "2026-02-03T11:15:53Z"`、`pushed_at: "2026-09-29T12:38:37Z"`、`stargazers_count: 273521`、`forks_count: 22982`、`open_issues_count: 543`。
- 描述（API 原文）：`"Skills for Real Engineers. Straight from my .agents directory."`；README 定位："My agent skills that I use every day to do real engineering - not vibe coding."
- 许可证：MIT（API `license.spdx_id: "mit"`）。
- 404 实证：无 404。反向证据：GitHub contents API 对未认证请求返回 403（IP 限流，原文 "API rate limit exceeded"），raw.githubusercontent.com 与 git clone 均正常；全量文件清单以下方浅克隆为准。

## 二、Skill 文件完整清单（路径 + 一句话职责）

全仓共 37 个 `SKILL.md`（engineering 20 / productivity 7 / in-progress 6 / misc 4）+ 15 个子参考 md。`engineering/` 与 `productivity/` 为 promoted 桶（进 Claude 插件分发），其余三桶按 `CLAUDE.md` 约定不进插件。

### engineering/（日常代码工作）

| 路径（前缀 `skills/engineering/`） | 职责 |
| --- | --- |
| `ask-matt/SKILL.md` | skill 路由器：按当前情境推荐该用哪个 skill/流程 |
| `grill-with-docs/SKILL.md` | 拷问式访谈 + 同步沉淀 `GLOSSARY.md` 与 ADR（组合调用 grilling + domain-modeling） |
| `triage/SKILL.md` | 把 issue 按状态机角色流转 |
| `improve-codebase-architecture/SKILL.md` | 扫描"加深模块"机会，出 HTML 报告再拷问用户逐个确认 |
| `setup-matt-pocock-skills/SKILL.md` | 每仓库一次性配置（issue tracker、triage 标签、文档位置） |
| `to-spec/SKILL.md` | 把当前会话合成为 spec 发布到 issue tracker，含 spec 模板与 Out of Scope 段 |
| `to-tickets/SKILL.md` | 把计划/spec/会话拆成带阻塞边的 tracer-bullet tickets |
| `implement/SKILL.md` | 按 spec/tickets 实施：seam 处驱动 /tdd，收尾 /code-review 再提交 |
| `implement-spec/SKILL.md` | 单集成分支实施整个 spec：任务图 + 并发 implementer 子代理 |
| `wayfinder/SKILL.md` | 超出单会话容量的大工作：拆成 issue tracker 上的决策票地图逐个解决 |
| `retro/SKILL.md` | 会话复盘：按类别给 agent 环境提改进（导航/自动检查/编码标准/steering 文件/工具经济） |
| `prototype/SKILL.md` | 一次性原型回答设计问题（LOGIC 单 HTML / UI 多变体两分支） |
| `diagnosing-bugs/SKILL.md` | 纪律化诊断循环：红 capable 反馈环 → 复现最小化 → 假设 → 探针 → 修复+回归测试 → 清理 |
| `research/SKILL.md` | 后台 agent 对一手高信任来源调研，产出带引用的 Markdown 笔记 |
| `tdd/SKILL.md` | 红绿循环 TDD 参考：好测试定义、seam 纪律、反模式、循环规则 |
| `domain-modeling/SKILL.md` | 主动构建领域模型：挑战术语、边缘场景压测、就地更新 GLOSSARY.md/ADR |
| `codebase-design/SKILL.md` | 深模块设计共享词汇（module/interface/seam/depth/adapter/leverage/locality）与原则 |
| `code-review/SKILL.md` | 双轴评审：Standards（仓库标准 + 12 条 Fowler smell 基线）与 Spec（忠实实现），并行子代理 |
| `pr/SKILL.md` | PR body 模板：Summary 视图 + Before/After 证据 + Merge Danger（单向/双向门 + 爆炸半径） |
| `wizard/SKILL.md` | 生成交互式 bash 向导，引导人完成只有人能做的步骤 |

### productivity/（通用工作流）

| 路径（前缀 `skills/productivity/`） | 职责 |
| --- | --- |
| `grill-me/SKILL.md` | 无情访谈用户，直到设计树每个分支都有答案 |
| `grilling/SKILL.md` | 访谈原语：design tree + frontier 分轮提问，事实自查、决策交用户 |
| `handoff/SKILL.md` | 把当前会话压缩成 handoff 文档交给下一个 agent |
| `teach/SKILL.md` | 跨会话教学，以当前目录为有状态教学工作区 |
| `to-questionnaire/SKILL.md` | 把独自答不了的决策变成问卷发出去异步填写 |
| `wait-what/SKILL.md` | 消息没听懂时触发：用 GLOSSARY 词汇重新讲一遍 |
| `writing-for-agents/SKILL.md` | 给 agent 写文档的写作参考：上下文指针、两级负载、信息层级、完成标准、leading words、剪枝 |

### in-progress/（beta，进插件）

`claude-handoff`、`loop-me`、`setup-ts-deep-modules`、`writing-beats`、`writing-fragments`、`writing-shape`（均为写作/会话流转实验 skill，与编码约束关系弱）。

### misc/（保留但不推广）

`git-guardrails-claude-code`、`migrate-to-shoehorn`、`scaffold-exercises`、`setup-pre-commit`。

### 子参考文件（15 个）

`tdd/tests.md`（好/坏测试对照示例）、`tdd/mocking.md`（mock 边界）、`codebase-design/DEEPENING.md`、`codebase-design/DESIGN-IT-TWICE.md`、`domain-modeling/ADR-FORMAT.md`、`domain-modeling/GLOSSARY-FORMAT.md`、`prototype/LOGIC.md`、`prototype/UI.md`、`improve-codebase-architecture/HTML-REPORT.md`、`productivity/writing-for-agents/SKILL-MECHANICS.md`、`teach/` 下 4 个格式文件、`triage/AGENT-BRIEF.md`、`triage/OUT-OF-SCOPE.md`、`ask-matt/PHASE-BOUNDARIES.md`。

另有仓库级文件：`CLAUDE.md`（仓库组织约定 + 全仓禁 em-dash）、`GLOSSARY.md`、`AGENTS.md`（9 字节指针）、README（四大失败模式论述）。

## 三、编码约束铁律提炼（原文要点，标注出处）

### A. 防瞎写代码（先理解、先复现、先对齐）

1. 诊断纪律："If you catch yourself reading code to build a theory before this command exists, stop: jumping straight to a hypothesis is the exact failure this skill prevents." —— 没有一个能变红的复现命令，禁止进入假设阶段。出处 `skills/engineering/diagnosing-bugs/SKILL.md` Phase 1。
2. 红 capable 命令四要素：驱动真实 bug 代码路径并断言用户的确切症状、确定性、秒级快、agent 可无人值守运行。出处同上。
3. 复现必须对上用户描述的症状："The loop produces the failure mode the user described... Wrong bug = wrong fix." 出处同上 Phase 2。
4. 假设必须可证伪并给出预测格式："If <X> is the cause, then <changing Y> will make the bug disappear"，说不出预测的假设是 vibe，丢弃。出处同上 Phase 3。
5. 探针一次只改一个变量；性能问题先建基线测量再修复（"Measure first, fix second"）。出处同上 Phase 4。
6. 动手前对齐需求：grilling 用 design tree + frontier 分轮访谈，frontier 空且用户确认共享理解后才行动；事实自查（派子代理），决策交用户。出处 `skills/productivity/grilling/SKILL.md`。
7. spec 先行：写 spec 前先探索仓库现状、 sketch 测试 seam 并与用户确认。出处 `skills/engineering/to-spec/SKILL.md` 步骤 1-2。

### B. 防只写注释/糊弄式交付

8. TDD 循环规则："Red before green. Write the failing test first, then only enough code to pass it. Don't anticipate future tests or add speculative features." 出处 `skills/engineering/tdd/SKILL.md` Rules of the loop。
9. 一次一个垂直切片："One seam, one test, one minimal implementation per cycle." 出处同上。
10. 横向切片反模式：先写全部测试再写全部实现 = 验证想象中的行为，测试对真实变化失去敏感度；要求垂直切片，每个测试是响应上一轮教训的 tracer bullet。出处同上 Anti-patterns。
11. 同义反复测试反模式："expect(add(a, b)).toBe(a + b)" 式断言按构造必然通过；期望值必须来自独立真理源（known-good 字面量、手算例子、spec）。出处同上 + `tdd/tests.md`。
12. 实现耦合测试反模式：mock 内部协作者、测私有方法、绕过接口直接查库验证；特征是"重构就红但行为没变"。出处同上 + `tdd/tests.md`。
13. 好测试像 spec："Tests verify behavior through public interfaces... A good test reads like a specification"，描述 WHAT 而非 HOW，一测一断言。出处 `tdd/SKILL.md` + `tdd/tests.md`。
14. mock 只在系统边界（外部 API、数据库、时间/随机、文件系统），自己控制的类/模块/内部协作者一律真实实现。出处 `tdd/mocking.md`。
15. 可验收的完成标准：每步以 completion criterion 收尾，"The strongest criteria are both checkable and exhaustive"；demand 驱动穷尽度（"Every modified model accounted for" 式的措辞逼出彻底工作）。出处 `skills/productivity/writing-for-agents/SKILL.md`。

### C. 修改范围控制

16. Spec 轴专查范围蔓延："behaviour in the diff that wasn't asked for (scope creep)"，逐条引用 spec 原文报告。出处 `skills/engineering/code-review/SKILL.md` 步骤 4。
17. 投机泛化 smell：spec 用不上的抽象/参数/钩子，"delete it; inline back until a real need shows"。出处同上 Fowler 基线。
18. seam 纪律："Test only at pre-agreed seams... No test is written at an unconfirmed seam"；选 seam 优先现有、用最高、理想数量是一。出处 `tdd/SKILL.md` + `to-spec/SKILL.md` 步骤 2。
19. 架构扫描先定范围："Scope before you scan: YAGNI"，权重给最近变更的热点路径。出处 `skills/engineering/improve-codebase-architecture/SKILL.md` 步骤 1。
20. 原型命名自证身份："name it so a casual reader can see it's a prototype, not production"，遵守项目既有路由约定，零新建顶层结构。出处 `skills/engineering/prototype/SKILL.md` 规则 1。
21. 原型零持久化、跳过 polish（无测试、仅可运行的错误处理、零抽象），完成后主分支只留验证过的决策。出处同上规则 3-4、6。

### D. 验证要求

22. 实施 agent 验证节奏："Run typechecking regularly, single test files regularly, and the full test suite once at the end." 完成后 /code-review 评审完才提交。出处 `skills/engineering/implement/SKILL.md`。
23. 双轴评审防互盲："Code that follows every standard but implements the wrong thing → Standards pass, Spec fail"，两轴并行子代理分开跑、分开报告，禁止合并重排。出处 `code-review/SKILL.md`。
24. Fowler smell 基线 12 条（Mysterious Name、Duplicated Code、Feature Envy、Data Clumps、Primitive Obsession、Repeated Switches、Shotgun Surgery、Divergent Change、Speculative Generality、Message Chains、Middle Man、Refused Beacon 遗传拒绝 Refused Bequest）；两条绑定规则：仓库文档化标准覆盖基线；每条 smell 都是判断题（"possible Feature Envy"），工具已强制的一律跳过。出处 `code-review/SKILL.md` 步骤 3。
25. 命名检验设计："Mysterious Name: a function, variable, or type whose name doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky." 出处同上。
26. 回归测试写在修复前但仅限正确 seam："If no correct seam exists, that itself is the finding"，记录并上报架构问题。出处 `diagnosing-bugs/SKILL.md` Phase 5。
27. 诊断收尾清单：原复现不再复、回归测试通过或记录无 seam、全部 `[DEBUG-...]` 探针 grep 清除、一次性原型删除、正确假设写进 commit/PR message。出处同上 Phase 6。
28. 调试日志强制唯一前缀（如 `[DEBUG-a4f2]`），"Cleanup at the end becomes a single grep"。出处同上 Phase 4。

### E. 命名/结构规范

29. 深模块原则："Design deep modules: a lot of behaviour behind a small interface"；deletion test（删掉后复杂度在 N 个调用点重现 = 它在挣饭吃）；interface 即测试面；"One adapter means a hypothetical seam. Two adapters means a real one." 出处 `skills/engineering/codebase-design/SKILL.md`。
30. 术语表纪律：module/interface/depth/seam 等词"Use these terms exactly"，替换成 component/service/API/boundary 即为漂移；变量、函数、文件用共享语言一致命名，agent 导航更省 token。出处同上 + README 失败模式 #2。
31. 可测试性三设计：接受依赖（依赖注入）、返回结果（副作用）、小表面积。出处同上 Designing for testability。
32. GLOSSARY.md 纯度："totally devoid of implementation details"，纯术语表。出处 `skills/engineering/domain-modeling/SKILL.md`。
33. spec 模板铁律：Implementation Decisions 段写具体文件路径与代码片段（"They may end up being outdated very quickly"），例外仅限原型产出的决策性片段；Out of Scope 段必填。出处 `to-spec/SKILL.md` 模板。
34. ADR 三条件门槛：难逆转 + 无上下文会令人惊讶 + 真实权衡结果，缺一跳过。出处 `domain-modeling/SKILL.md`。

### F. 提示词/文档写法纪律（写系统提示词时的元规则）

35. 正面陈述优于禁令："steering by prohibition drags the forbidden behaviour into context and makes it more available"；先说目标行为，让被禁行为一次都别被说出来；禁令仅保留给无法正面表述的硬护栏，且配对正面目标。出处 `skills/productivity/writing-for-agents/SKILL.md` Negation 节。
36. 单一真理源 + 环境缓存原则：文档复述环境（package.json scripts、目录布局）= cache，只缓存查不到的（未成文约定、选择背后的原因、坑）。出处同上 Pruning 节。
37. no-op 猎杀：模型默认就遵守的指令是纯负担，逐句测试"是否改变默认行为"，失败就删整句；弱词（be thorough）升级成强词（relentless）。出处同上。
38. leading words：用模型预训练已有的紧凑概念词（tight、red、tracer bullets），一个 token 锚定一整片行为。出处同上。
39. 文档分层：AGENTS.md/CLAUDE.md 极简、通常只放导航指针；CODING_STANDARDS.md 评审时读、实施时读；机械违规给确定性检查（linter/pre-commit/CI），判断题才进标准文档；编码标准由 review agent 施加（实施 agent 上下文压力最大）。出处 `skills/engineering/retro/SKILL.md`。
40. 全仓写作约定：所有 prose 禁用 em-dash，遇到时重写句子（逗号/冒号/句号/括号/连词），零盲目字符替换。出处 `CLAUDE.md` 末段。

## 四、可融入 Climber 内置提示词的条目建议（中文大白话，每条一行）

1. 动手改码前先探索仓库现状，读术语表和领域决策记录，理解先于编辑。
2. 每轮只交付一个最小垂直切片：一个接口点、一个测试、一份刚好够的实现。
3. 先写会失败的测试，再写刚好让它通过的代码，多写的功能都是投机。
4. 测试只测公共接口的行为，测私有方法、mock 内部协作者的测试直接重写。
5. 断言的期望值必须来自独立事实，照代码逻辑重算期望值的测试等于没测。
6. 验证走接口本身，绕过接口直接查库查状态的断言一律改掉。
7. 只在系统边界做 mock，自己写的模块用真实实现参与测试。
8. 测试一个一个按场景写，先攒一堆测试再攒一堆实现的横向切法禁止。
9. 重构归评审阶段，写新功能的循环里只加刚好够的代码。
10. 写码过程中定期跑类型检查和单个测试文件，收尾必须全量测试通过再提交。
11. 提交前按两轴自查：代码规范轴和需求忠实轴，两轴分开各过一遍再合报告。
12. 自查时专抓 diff 里用户没要求的行为，抓到就撤掉。
13. spec 没要的抽象、参数、钩子直接删，等真需求出现再加回来。
14. 命名要能说出这个东西干什么，起不出诚实的名字说明设计有问题。
15. 一个概念在代码、文档、对话里保持同一个词，项目有术语表就照术语表命名。
16. 模块设计追求小接口大实现，接口和内部一样复杂的浅模块是坏味道。
17. 修 bug 先造一个能变红的复现命令，复现命令没跑出来就停下，盯着代码猜原因是大忌。
18. 复现必须命中用户描述的那个症状，修错 bug 比不修更糟。
19. 调试探针一次只改一个变量，调试日志加唯一前缀，收尾一次搜索清干净。
20. 性能问题先建基线测量再动手修，靠感觉优化等于盲改。
21. 给 Agent 写规则用正面陈述，禁令句式会把禁止的行为拉进上下文反而更容易犯。
22. 模型默认就会做的指令删掉，每条规则都要能改变默认行为才配留在提示词里。

## 五、与 Climber docs/references/prompt-repos.md 已有条目的重合度

- **Aider lazy_prompt（杜绝只写注释糊弄）**：低重合、互补。mattpocock/skills 无逐字对应条目；等价能力由 TDD 纪律承载——交付物以"能变红再变绿的测试"计，纯注释/骨架代码过不了 tdd 与 code-review 两关。lazy_prompt 的"防注释糊弄"可保留，作为 TDD 之外的兜底。
- **Aider overeager_prompt（控制修改范围）**：高度重合，且本仓库给出五处独立同源支撑：code-review Spec 轴的 scope creep 专项（`code-review/SKILL.md`）、tdd 的 "Don't anticipate future tests or add speculative features"（`tdd/SKILL.md`）、Speculative Generality smell（`code-review/SKILL.md`）、"Scope before you scan: YAGNI"（`improve-codebase-architecture/SKILL.md`）、原型"零新建顶层结构"（`prototype/SKILL.md`）。建议 overeager 条目以本仓库为最强引用源合并。
- **SWE-agent 五步流程（查找→复现→修复→确认→边界）**：高重合。`diagnosing-bugs/SKILL.md` 六阶段循环（feedback loop → reproduce+minimise → hypothesise → instrument → fix+regression test → cleanup）是它的加严版，核心增量在"无红 capable 命令禁止进入假设"这一硬门。
- **Claude Code APEI（理解先于行动，计划先于编辑）**：中高重合。`grilling/SKILL.md` 的 design tree + frontier + 用户确认后行动，是该原则的可操作化版本。
- **mini-swe-agent（响应格式约束）**：零重合。本仓库约束过程纪律与产出质量，管响应格式的部分仅 pr/SKILL.md 的 PR body 模板。
- **OpenHands/Devstral（角色 + 质量规范）**：中低重合。retro/SKILL.md 的"标准由 review agent 施加、机械违规进 linter、判断题进标准文档"是独有的分层增量。
- **结论**：在"范围控制""复现先行"两处本仓库可作为 Climber 现有条目的最强引用源合并；在"测试反模式三宗罪（同义反复/实现耦合/横向切片）""双轴评审分离""调试日志前缀清理""正面陈述写法""no-op 猎杀"五处为纯增量，按第四节清单融入后即补齐 Climber 提示词体系的缺口。
