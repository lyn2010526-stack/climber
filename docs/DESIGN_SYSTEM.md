# Climber 设计系统与前端扩展规则

## 1. 适用范围

Climber 当前的主要产品表面是 Python/FastAPI 后端，`app/static/` 只有少量 HTML 文件。本文档为这些 HTML 提供轻量、可迁移的视觉约束；它不把仓库描述为 uni-app 项目。仓库已有 `frontend-react/`，只有任务明确扩展该目录时，才执行本文档的组件库评估流程。

## 2. 先定风格，再写组件

新增或明显改造 UI 前，先在任务说明中确定：

- 目标表面：`app/static/` HTML、`frontend-react/`，或两者之一。
- 信息层级：页面标题、主要操作、次要操作、状态和错误反馈。
- 交互状态：默认、悬停、聚焦、禁用、加载、成功、错误、空数据。
- 响应式边界：当前视口假设、窄屏行为、内容溢出策略。
- 无障碍要求：语义元素、键盘焦点、标签关联、对比度和错误提示。

先定义 Token，再落地具体样式。Token 应表达语义，不应把颜色值散落在 HTML 或组件中。

## 3. 基础 Token

当前轻量 HTML 表面使用以下语义 Token。新增值必须说明使用场景，并优先扩展语义层：

```css
:root {
  --color-bg: #f7f8fa;
  --color-surface: #ffffff;
  --color-text: #17202a;
  --color-text-muted: #667085;
  --color-border: #d9dee7;
  --color-primary: #2563eb;
  --color-primary-contrast: #ffffff;
  --color-success: #15803d;
  --color-warning: #b45309;
  --color-danger: #b42318;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgb(16 24 40 / 8%);
  --shadow-md: 0 4px 12px rgb(16 24 40 / 12%);
  --font-sans: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
  --text-sm: 0.875rem;
  --text-md: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.5rem;
}
```

这些 Token 是稳定的起点，页面可按现有品牌资产和可用性证据演进。业务状态必须使用 `success`、`warning`、`danger` 等语义名，避免直接绑定色相名称。

## 4. 组件与重复模式

- 相同语义的按钮、表单控件、状态提示、卡片和错误反馈必须复用同一结构与 Token。
- 第二次出现相同交互模式时，先抽取共享类、模板片段或 React 组件，再继续复制。
- 组件 API 只暴露必要的变体；变体命名表达语义，例如 `primary`、`danger`、`compact`。
- 组件应覆盖默认、焦点、禁用、加载、错误和空状态；缺少状态时必须在任务说明中标记。
- `app/static/` 中的简单页面优先使用原生 HTML、CSS 和少量脚本；新增依赖需要有性能、维护或可复用性理由。

## 5. 组件库决策

组件库评估只在明确扩展 `frontend-react/`、新增大量交互组件，或用户明确要求引入时执行。流程如下：

1. 盘点现有组件、Token、依赖、构建和测试能力。
2. 比较无库、现有库和候选库的可访问性、主题能力、包体积、许可证、维护状态和与现有技术栈的兼容性。
3. 记录选择、放弃选项、迁移成本和验证方案；未经记录不得新增 UI 框架或组件库依赖。
4. 先用一个代表性组件验证样式、键盘操作、构建和测试，再扩大使用范围。

当前仓库事实支持 React 前端扩展场景，但不构成引入新库的决定。uni-app 不属于当前技术栈和默认决策路径。

## 6. 快照与视觉验证

当前 `app/static/` 没有独立的快照基线，已有 React 测试位于 `frontend-react/src/**/__tests__/`。涉及 UI 的任务应选择适用验证：

- HTML：使用浏览器或 Playwright 检查语义、关键状态、窄屏布局和资源加载。
- React：运行对应 Vitest/Playwright 测试；新增稳定视觉表面时才建立快照。
- 快照必须审阅差异并说明原因，禁止通过更新快照掩盖行为回归。

## 7. 相关文档

- 开发执行规则：`docs/DEVELOPMENT_RULES.md`
- 文档索引：`docs/DEVELOPMENT_RULES.md` 的“相关文档与来源”章节
- 系统架构：`docs/ARCHITECTURE.md`

## 来源

- W3C WCAG 2.2: https://www.w3.org/TR/WCAG22/
- Material Design 3 Design Tokens: https://m3.material.io/foundations/design-tokens/overview
- GitHub Primer Design System: https://primer.style/
- React Testing Library Principles: https://testing-library.com/docs/guiding-principles/
