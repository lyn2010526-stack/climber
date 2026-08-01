# Requirements Document

## Introduction

本功能为 Climber 平台引入双独立开关控制系统，分别控制「自治智能体模式」与「Token 节流代码检索 MCP」，实现四种自由组合运行逻辑。基础主系统提示词永久常驻，节流约束仅作为附加片段动态追加；MCP 进程与 Agent 核心引擎解耦，确保单点故障不影响整体可用性。

## Glossary

- **自治智能体模式**: 加载高级自主 Agent 底层系统提示词，解锁任务拆解、自动规划、持续执行、结果自省复盘能力
- **Token 节流 MCP**: 启动 jCodeMunch 索引服务，动态追加代码定向检索约束提示，禁止一次性读取完整项目文件夹
- **基础主系统提示词**: 永久常驻的核心对话提示词，禁止整体替换
- **附加约束片段**: 动态追加或移除的提示词片段，仅包含节流规则与检索约束
- **MCP 进程**: 独立的代码检索服务进程，与 Agent 核心引擎通过 IPC/HTTP 通信
- **开关组合**: 两个独立开关的四种状态组合

## Requirements

### Requirement 1: 设置面板双开关 UI

**User Story:** AS 用户, I want 在设置面板中看到两个完全独立的开关, so that 我可以自由组合自治智能体模式与 Token 节流 MCP 的运行状态。

#### Acceptance Criteria

1. WHEN 用户进入设置面板, 系统 SHALL 显示「自治智能体模式」与「Token 节流｜代码定向检索 MCP」两个独立开关
2. WHEN 用户切换任意开关, 系统 SHALL 立即生效且不联动另一个开关
3. WHEN 开关状态发生变化, 系统 SHALL 在界面上显示对应的辅助说明小字
4. WHILE 用户停留在设置面板, 系统 SHALL 保持当前开关状态并支持实时预览运行模式说明
5. IF 用户未登录, 系统 SHALL 显示开关但标记为"需要登录后生效"

### Requirement 2: 四种开关组合运行逻辑

**User Story:** AS 系统, I want 支持四种开关组合的完整运行逻辑, so that 不同用户场景需求得到满足。

#### Acceptance Criteria

1. WHEN 自治智能体=关闭, Token 节流 MCP=关闭, 系统 SHALL 运行普通对话模式, 使用基础主系统提示词, 不加载高级提示词, 不启动 MCP
2. WHEN 自治智能体=开启, Token 节流 MCP=关闭, 系统 SHALL 加载高级自主 Agent 提示词, 启用任务拆解/自动规划/持续执行/结果自省复盘, 不启动 MCP
3. WHEN 自治智能体=关闭, Token 节流 MCP=开启, 系统 SHALL 保持基础主系统提示词, 启动 jCodeMunch MCP, 追加代码定向检索约束提示
4. WHEN 自治智能体=开启, Token 节流 MCP=开启, 系统 SHALL 加载高级自主 Agent 提示词, 启动 jCodeMunch MCP, 追加节流规则附加片段
5. WHILE 系统运行中, 系统 SHALL 基础主系统提示词永久常驻, 附加约束片段仅动态追加/移除, 禁止整体替换整套 Prompt

### Requirement 3: MCP 进程解耦与容错

**User Story:** AS 系统, I want MCP 进程与 Agent 核心引擎互相解耦, so that MCP 异常不会导致主 Agent 瘫痪。

#### Acceptance Criteria

1. WHEN 用户开启 Token 节流 MCP, 系统 SHALL 异步启动 jCodeMunch MCP 进程
2. IF MCP 进程启动失败, 系统 SHALL 显示弹窗提示"代码检索服务启动失败, 对话功能仍可使用", 不阻断主 Agent 对话
3. IF MCP 进程加载超时, 系统 SHALL 在 10 秒后触发超时处理, 显示提示并断开 MCP
4. IF MCP 进程运行中崩溃, 系统 SHALL 自动尝试重启最多 3 次, 超过后标记为失效并通知用户
5. WHEN MCP 进程失效, 系统 SHALL 移除附加约束片段, 降级为基础主系统提示词模式, 主 Agent 对话与工具调用保持可用

### Requirement 4: 模块加载时序

**User Story:** AS 系统, I want 明确的模块加载时序, so that 会话创建与提示片段追加时机可控。

#### Acceptance Criteria

1. WHEN 用户创建新会话, 系统 SHALL 首先加载基础主系统提示词
2. WHEN 会话初始化完成, IF 自治智能体模式开启, 系统 SHALL 追加高级自主 Agent 提示词片段
3. WHEN 会话初始化完成, IF Token 节流 MCP 开启且 MCP 就绪, 系统 SHALL 追加代码定向检索约束片段
4. WHEN 用户切换开关状态, 系统 SHALL 在下一轮对话开始时应用新提示词组合
5. WHEN MCP 就绪状态变化, 系统 SHALL 动态更新附加约束片段, 不中断当前对话

### Requirement 5: 多端 UI 适配

**User Story:** AS 用户, I want 设置面板在网页、PC、移动端均有良好体验, so that 我可以随时随地调整 Agent 行为。

#### Acceptance Criteria

1. WHEN 用户在 PC 端访问设置面板, 系统 SHALL 以桌面布局展示双开关, 辅助说明文字位于开关右侧
2. WHEN 用户在移动端访问设置面板, 系统 SHALL 以移动布局展示双开关, 辅助说明文字位于开关下方
3. WHEN 用户切换开关, 系统 SHALL 显示 300ms 过渡动画反馈
4. WHEN 开关处于开启状态, 系统 SHALL 使用主题色高亮显示
5. WHEN 开关处于关闭状态, 系统 SHALL 使用灰色显示
