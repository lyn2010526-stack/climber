# Climber 持续执行计划（活跃）

> 维护规则：每完成一项就更新状态；本文件是长任务的唯一进度锚点，重启后先读它。
> 来源：用户设计总纲（33 页 DOCX，本地已解压全文）+ 用户多轮口头指令。

## 一、内置提示词强化（用户最高优先级，反复强调"强行内置"）

- [ ] 融合 mattpocock/skills 编码约束精华 → core.system v1.2.0 + 新 skill
- [ ] 融合 sliver-vibe-coding 开发治理精华（防假完成/任务分级）→ core.system + 新 skill
- [ ] 融合 x1xhlol/system-prompts 底层宪法（研究补跑中）
- [ ] 融合 awesome-design-md UI 铁律 → 新 skill ui_design_discipline
- [ ] 融合 anysearch skill/MCP 搜索规范 → 新 skill search_discipline
- [ ] 融合 awesome-cursorrules + 12-factor-agents 可靠性原则 → core.system
- [ ] 融合 graphify + sliver 宪法模板（研究补跑中）
- [ ] 融合 spec-kit + agent-maxxing + CodeWhale + agency-agents（研究补跑中）
- 落地位置：`app/core/prompts/registry.py`（CORE_BODY 升版，旧版保留 deprecated）、`app/skills/definitions.py` + `app/skills/builtins.py`

## 二、50 个开源参考项目深挖（设计总纲第五部分）

- 已完成：#41 Zep、#42-50 全部（9 篇 deep-dives + opensource-eval-42-50.md）
- 待深挖：#1-40（一组调度 12 + 二组世界模型 8 + 三组前端 12 + 四组记忆画像 9）
- 产出要求：每项目源码级结论 + Climber 映射 + 证据等级，落 `docs/references/deep-dives/`

## 三、8000 端口全面核实与修复

- [ ] 后端 SPA 构建产物 + API 全面健康检查
- [ ] 逐 API 端点验证（openapi 187 路径）
- [ ] 前端构建产物与运行时问题排查
- [ ] 发现的问题逐项修复

## 四、设计总纲剩余落地项

- [ ] 阶段 3：遗传进化过渡（提示词&参数种群进化）—— 进化引擎已扩展，接入评估闭环
- [ ] 阶段 4：agi-core 世界模型 + 因果挖掘 + 神经进化
- [ ] 画像算法输出接入意图理解/检索排序/回归评估闭环
- [ ] 20 个顶级 AI 产品系统提示词结构对照（prompt-repos.md 已索引，持续提炼）
- [ ] 提示词/技能版本管理、过期标记、回滚（registry 已具备，持续维护）

## 五、执行纪律

- 每轮完成即提交（按领域），不留脏工作区
- 全量回归基线：`python3 -m pytest tests/ -q`（2026-10-01 时点 1150 passed）
- 研究报告一律带证据等级；404 项目实证不冒充
- 不停机：每轮结束从本文件取下一项继续
