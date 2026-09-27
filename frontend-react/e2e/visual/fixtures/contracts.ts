/**
 * Deterministic backend fixtures for the visual-regression matrix.
 *
 * Every shape below is transcribed from the real client contract in
 * `src/api.ts` / `src/types/api.ts` — the response keys are the ones the app
 * actually reads, so a page that renders a fixture is exercising its real
 * render path rather than a `Loading...` fallback. When a contract drifts, the
 * fixture drifts with it and the page under test shows up as a real defect
 * instead of silently rendering an empty list.
 *
 * Nothing here talks to a server: the router in `./routes.ts` answers every
 * request from this table, which is what keeps the matrix reproducible while
 * the backend is offline.
 */

import type {
  Agent,
  Crew,
  Plugin,
  Skill,
  Workflow,
  HealthCheck,
  Message,
  Session,
} from '../../../src/types/api';
import type {
  ApiSession,
} from '../../../src/store/workspace';
import type {
  SessionMessage,
  TaskSummary,
  ArcBenchStatus,
  PermissionConfigOut,
} from '../../../src/api';

/** Frozen so a mutation inside a test cannot leak into the next one. */
const fixedDate = '2026-01-15T08:30:00.000Z';

export const FIXTURE_SESSION_ID = 'sess-fixture-0001';
export const FIXTURE_USER_ID = 'user-fixture-0001';

// ---------------------------------------------------------------------------
// Chat / sessions — api.ts:338-361
// ---------------------------------------------------------------------------

export const sessions: ApiSession[] = [
  {
    id: FIXTURE_SESSION_ID,
    title: '视觉回归基线会话',
    status: 'idle',
    created_at: fixedDate,
    updated_at: fixedDate,
    provider: 'openai',
    model_id: 'gpt-4o-mini',
    agent_id: 'agent-fixture-0001',
  },
  {
    id: 'sess-fixture-0002',
    title: '长会话用于验证侧栏滚动',
    status: 'completed',
    created_at: fixedDate,
    updated_at: fixedDate,
    provider: 'anthropic',
    model_id: 'claude-sonnet-4-20250514',
    agent_id: null,
  },
  {
    id: 'sess-fixture-0003',
    title: '失败会话',
    status: 'failed',
    created_at: fixedDate,
    updated_at: fixedDate,
    provider: null,
    model_id: null,
    agent_id: 'agent-fixture-0001',
  },
];

/** `GET /sessions` returns the bare array shape `ApiSession`. */
export const createSessionResponse: ApiSession = {
  id: FIXTURE_SESSION_ID,
  title: '视觉回归基线会话',
  status: 'idle',
  created_at: fixedDate,
  updated_at: fixedDate,
  provider: 'openai',
  model_id: 'gpt-4o-mini',
  agent_id: 'agent-fixture-0001',
};

/** `SessionMessage` — api.ts:60-73. `tool_calls` and friends are always present. */
function message(
  id: string,
  role: SessionMessage['role'],
  content: string,
  overrides: Partial<SessionMessage> = {},
): SessionMessage {
  return {
    id,
    role,
    content,
    tool_call_id: null,
    tool_calls: [],
    tool_name: null,
    created_at: fixedDate,
    ...overrides,
  };
}

export const sessionMessages: SessionMessage[] = [
  message('msg-fixture-0001', 'user', '请检查移动端底部导航与输入框是否重叠。'),
  message(
    'msg-fixture-0002',
    'assistant',
    [
      '已检查三处关键区域：',
      '',
      '1. **底部导航** `.mobile-bottom-nav` 为 `position: fixed`，内容区通过 `--mobile-nav-reserve` 预留了等高空间，两者不重叠。',
      '2. **输入区** 在移动端由 `.mobile-content` 的 `padding-bottom` 兜底。',
      '3. **Send 按钮** 尺寸 `44x44`，位于输入行末尾，未被导航遮挡。',
      '',
      '结论：**无重叠**。',
    ].join('\n'),
  ),
  message(
    'msg-fixture-0003',
    'assistant',
    '正在执行 `read_file` 以确认断点。',
    {
      tool_name: 'read_file',
      tool_call_id: 'tc-fixture-0001',
      tool_calls: [
        {
          id: 'tc-fixture-0001',
          function: { name: 'read_file', arguments: '{"path":"src/index.css"}' },
        },
      ],
    },
  ),
  message('msg-fixture-0004', 'tool', '读取到 1300 行样式定义。', { tool_name: 'read_file' }),
  message(
    'msg-fixture-0005',
    'assistant',
    '表格、代码与长单词的换行行为均已覆盖：\n\n| 断点 | 布局 | 触控目标 |\n| --- | --- | --- |\n| 1440 | 侧栏展开 | 44px |\n| 768 | 侧栏展开 | 44px |\n| 390 | 底部导航 | 56px |\n\n`supercalifragilisticexpialidocious-antidisestablishmentarianism-pneumonoultramicroscopicsilicovolcanoconiosis` 用于验证 `overflow-wrap: anywhere`。',
  ),
];

/** `Message` (render-layer type, MessageBubble.tsx:8-24) for the empty-state contrast. */
export const emptyMessages: Message[] = [];

// ---------------------------------------------------------------------------
// Agents / tools / models — api.ts:321, 403, 408
// ---------------------------------------------------------------------------

export const agents: Agent[] = [
  { id: 'agent-fixture-0001', name: '视觉审查员', provider: 'openai', model_id: 'gpt-4o-mini', created_at: fixedDate },
  { id: 'agent-fixture-0002', name: 'RegressionHunter', provider: 'anthropic', model_id: 'claude-sonnet-4-20250514', created_at: fixedDate },
  { id: 'agent-fixture-0003', name: '成本审计', provider: 'google', model_id: 'gemini-2.5-pro', created_at: fixedDate },
];

export const tools = [
  { id: 'tool-fixture-0001', name: 'read_file', description: '读取工作区文件', category: 'filesystem', enabled: true },
  { id: 'tool-fixture-0002', name: 'write_file', description: '写入工作区文件', category: 'filesystem', enabled: true },
  { id: 'tool-fixture-0003', name: 'web_search', description: '联网检索', category: 'network', enabled: false },
  { id: 'tool-fixture-0004', name: 'run_shell', description: '在沙箱内执行命令', category: 'execution', enabled: true },
];

export const models = [
  { id: 'gpt-4o-mini', provider: 'openai', label: 'GPT-4o mini' },
  { id: 'claude-sonnet-4-20250514', provider: 'anthropic', label: 'Claude Sonnet 4' },
  { id: 'gemini-2.5-pro', provider: 'google', label: 'Gemini 2.5 Pro' },
];

// ---------------------------------------------------------------------------
// Skills / MCP / plugins — api.ts:552-611, 826-844
// ---------------------------------------------------------------------------

export const skills: Skill[] = [
  { id: 'skill-fixture-0001', name: '网页截图', description: '使用无头浏览器对指定 URL 截图', category: 'browser', enabled: true },
  { id: 'skill-fixture-0002', name: '代码审查', description: '对变更文件做静态检查并输出结构化结论', category: 'quality', enabled: true },
  { id: 'skill-fixture-0003', name: '数据清洗', description: '读取 CSV 并按规则归一化字段', category: 'data', enabled: false },
  { id: 'skill-fixture-0004', name: '报告生成', description: '把分析结果渲染为 Markdown 报告', category: 'content', enabled: true },
];

export const mcpServers = [
  { id: 'mcp-fixture-0001', name: 'filesystem', status: 'connected', transport: 'stdio', command: 'npx -y @modelcontextprotocol/server-filesystem', tools_count: 12 },
  { id: 'mcp-fixture-0002', name: 'github', status: 'connected', transport: 'sse', url: 'https://mcp.example.test/sse', tools_count: 34 },
  { id: 'mcp-fixture-0003', name: 'postgres', status: 'error', transport: 'stdio', command: 'uvx mcp-server-postgres', tools_count: 0, error: 'ECONNREFUSED 127.0.0.1:5432' },
  { id: 'mcp-fixture-0004', name: 'memory', status: 'disconnected', transport: 'sse', url: 'https://mcp.example.test/memory', tools_count: 6 },
];

export const mcpCategories = [
  { id: 'cat-fixture-0001', name: '文件系统', count: 4 },
  { id: 'cat-fixture-0002', name: '数据库', count: 7 },
  { id: 'cat-fixture-0003', name: '协作', count: 11 },
];

/**
 * `Plugin` (types/api.ts:46-52) declares the status fields only; `type` is part
 * of the payload the plugins endpoints actually return and the list view keys
 * its filter on, so the fixture carries it via the extension the contract leaves
 * open. Widening here (rather than editing the product type) keeps the fixture
 * honest about which fields are declared and which are observed.
 */
export type PluginFixture = Plugin & { type: string };

export const plugins: PluginFixture[] = [
  { id: 'plugin-fixture-0001', name: 'climber-telemetry', description: '把运行指标发送到内部时序库', is_enabled: true, status: 'active', type: 'mcp' },
  { id: 'plugin-fixture-0002', name: 'safe-shell', description: '为 shell 工具增加命令白名单', is_enabled: true, status: 'active', type: 'hook' },
  { id: 'plugin-fixture-0003', name: 'legacy-exporter', description: '旧版导出插件，待迁移', is_enabled: false, status: 'inactive', type: 'mcp' },
  { id: 'plugin-fixture-0004', name: 'cost-guard', description: '按预算阈值阻断调用', is_enabled: false, status: 'pending', type: 'hook' },
];

export const marketplace = {
  total: 4,
  page: 1,
  page_size: 20,
  items: [
    { id: 'mkt-fixture-0001', name: 'vector-store', description: 'Chroma 向量检索', type: 'mcp', installs: 1280, rating: 4.7 },
    { id: 'mkt-fixture-0002', name: 'sandbox-guard', description: '沙箱命令审计', type: 'hook', installs: 640, rating: 4.2 },
    { id: 'mkt-fixture-0003', name: 'trace-exporter', description: '导出分布式追踪', type: 'mcp', installs: 312, rating: 4.4 },
  ],
};

export const pluginCategories = [
  { id: 'pcat-0001', name: 'MCP 服务', count: 2 },
  { id: 'pcat-0002', name: '钩子', count: 2 },
];

// ---------------------------------------------------------------------------
// Workflows / crews / groups — api.ts:413-538
// ---------------------------------------------------------------------------

export const workflows: Workflow[] = [
  {
    id: 'wf-fixture-0001',
    name: '截图回归流水线',
    description: '对目标页面执行多宽度截图并汇总结构断言结果',
    nodes: [
      { id: 'n1', type: 'input', position: { x: 0, y: 0 }, data: { label: '输入 URL' } },
      { id: 'n2', type: 'agent', position: { x: 220, y: 0 }, data: { label: '执行审查' } },
      { id: 'n3', type: 'output', position: { x: 440, y: 0 }, data: { label: '报告' } },
    ],
    edges: [
      { id: 'e1', source: 'n1', target: 'n2' },
      { id: 'e2', source: 'n2', target: 'n3' },
    ],
    is_template: false,
    run_count: 128,
    last_status: 'succeeded',
    created_at: fixedDate,
  },
  {
    id: 'wf-fixture-0002',
    name: '成本巡检',
    description: '每日汇总 token 消耗并比对预算',
    nodes: [{ id: 'n1', type: 'cron', position: { x: 0, y: 0 }, data: { label: '每日 09:00' } }],
    edges: [],
    is_template: true,
    run_count: 0,
    last_status: undefined,
    created_at: fixedDate,
  },
];

export const crews: Crew[] = [
  { id: 'crew-fixture-0001', name: '审查小队', tasks: [{ id: 't1', title: '结构审查' }, { id: 't2', title: '像素比对' }], created_at: fixedDate },
  { id: 'crew-fixture-0002', name: '发布小队', tasks: [{ id: 't3', title: '构建' }, { id: 't4', title: '发布' }], created_at: fixedDate },
];

export const documents = [
  { id: 'doc-fixture-0001', name: '视觉回归规范.md', size_bytes: 18_442, collection: 'handbook', updated_at: fixedDate },
  { id: 'doc-fixture-0002', name: 'API 契约速查.md', size_bytes: 6_120, collection: 'handbook', updated_at: fixedDate },
  { id: 'doc-fixture-0003', name: '故障排查记录.md', size_bytes: 42_881, collection: 'runbooks', updated_at: fixedDate },
];

export const groups = [
  { id: 'group-fixture-0001', name: '视觉回归组', description: '负责双主题视觉基线', topic: 'visual regression', members: 3, status: 'active', created_at: fixedDate },
  { id: 'group-fixture-0002', name: '后端契约组', description: '维护 API 契约一致性', topic: 'contracts', members: 2, status: 'idle', created_at: fixedDate },
];

// ---------------------------------------------------------------------------
// Tasks / cost / stats / cluster — api.ts:698-736, 475-497
// ---------------------------------------------------------------------------

export const tasks: TaskSummary[] = [
  { task_id: 'task-fixture-0001', objective: '对 chat 页面执行 5 宽度结构断言', status: 'running', progress: 62, total_steps: 8, created_at: fixedDate },
  { task_id: 'task-fixture-0002', objective: '生成 dark 主题基线', status: 'completed', progress: 100, total_steps: 5, created_at: fixedDate },
  { task_id: 'task-fixture-0003', objective: '校验触控目标不小于 44px', status: 'failed', progress: 30, total_steps: 4, created_at: fixedDate },
  { task_id: 'task-fixture-0004', objective: '排队中的任务', status: 'pending', progress: 0, total_steps: 3, created_at: fixedDate },
];

export const taskDetail = {
  task_id: 'task-fixture-0001',
  objective: '对 chat 页面执行 5 宽度结构断言',
  status: 'running',
  progress: 62,
  total_steps: 8,
  created_at: fixedDate,
  result: { overlaps: 0, overflow: 0, min_touch_target_px: 44 },
  error: null,
  started_at: fixedDate,
  finished_at: null,
};

export const costUsage = {
  total_cost: 12.8471,
  total_tokens: 4_820_133,
  total_calls: 3182,
  by_model: [
    { model: 'gpt-4o-mini', cost: 6.2144, tokens: 2_100_000, calls: 1910 },
    { model: 'claude-sonnet-4-20250514', cost: 5.9021, tokens: 1_980_000, calls: 1042 },
    { model: 'gemini-2.5-pro', cost: 0.7306, tokens: 740_133, calls: 230 },
  ],
  by_day: [
    { date: '2026-01-11', cost: 1.42, tokens: 512000 },
    { date: '2026-01-12', cost: 1.88, tokens: 690000 },
    { date: '2026-01-13', cost: 2.05, tokens: 741000 },
    { date: '2026-01-14', cost: 3.11, tokens: 1204000 },
    { date: '2026-01-15', cost: 4.3871, tokens: 1676133 },
  ],
};

export const costBudget = {
  amount: 80,
  period: 'monthly',
  is_active: true,
  current_spend: 12.8471,
  per_session_limit: 5,
  per_request_limit: null,
};

export const stats = {
  total_users: 7,
  total_agents: 3,
  total_sessions: 1284,
  total_api_keys: 4,
};

export const clusterStatus = {
  state: 'ready',
  nodes: 4,
  total_tokens: 182_400,
  active_agents: 3,
  updated_at: fixedDate,
};

// ---------------------------------------------------------------------------
// Doctor / traces / eval / reasoning — DoctorPage.tsx, TraceViewer.tsx, EvalDashboard.tsx
// ---------------------------------------------------------------------------

export const doctorReport = {
  healthy: true,
  sections: [
    {
      name: 'runtime',
      checks: [
        { section: 'runtime', name: 'python 版本', ok: true, detail: '3.12.4' },
        { section: 'runtime', name: '事件循环', ok: true, detail: 'uvloop' },
      ],
    },
    {
      name: 'storage',
      checks: [
        { section: 'storage', name: 'postgres', ok: true, detail: 'latency 3ms' },
        { section: 'storage', name: 'redis', ok: true, detail: 'latency 1ms' },
        { section: 'storage', name: 'chroma', ok: false, detail: 'collection 未初始化' },
      ],
    },
    {
      name: 'providers',
      checks: [
        { section: 'providers', name: 'openai', ok: true, detail: 'reachable' },
        { section: 'providers', name: 'anthropic', ok: true, detail: 'reachable' },
      ],
    },
  ],
};

export const traces = [
  { trace_id: 'trace-fixture-0001', name: 'chat.sse.stream', service: 'climber-api', started_at: fixedDate, duration_ms: 1840, spans_count: 12, status: 'ok' },
  { trace_id: 'trace-fixture-0002', name: 'agent.run', service: 'climber-worker', started_at: fixedDate, duration_ms: 9210, spans_count: 47, status: 'ok' },
  { trace_id: 'trace-fixture-0003', name: 'mcp.tools.call', service: 'climber-mcp', started_at: fixedDate, duration_ms: 320, spans_count: 3, status: 'error' },
];

export const traceDetail = {
  spans: [
    { span_id: 's1', name: 'POST /sessions', parent_id: null, start_ms: 0, duration_ms: 42, attributes: { 'http.status_code': 201 } },
    { span_id: 's2', name: 'chat.stream', parent_id: 's1', start_ms: 44, duration_ms: 1798, attributes: { 'llm.model': 'gpt-4o-mini', 'llm.tokens': 812 } },
  ],
  stats: { total_spans: 12, errors: 0, total_duration_ms: 1840 },
};

export const evalDatasets = [
  { id: 'ds-fixture-0001', name: '视觉回归基准', cases: 120, description: '覆盖 5 个宽度的结构断言用例' },
  { id: 'ds-fixture-0002', name: '工具调用准确率', cases: 48, description: '评估工具选择正确率' },
  { id: 'ds-fixture-0003', name: '长上下文稳定性', cases: 12, description: '128k 上下文下的截断行为' },
];

export const reasoningModes = [
  { id: 'mode-fixture-0001', name: 'tree_of_thought', label: '思维树', max_paths: 5, description: '并行展开多条推理路径' },
  { id: 'mode-fixture-0002', name: 'self_consistency', label: '自洽性', max_paths: 8, description: '多次采样取多数结论' },
  { id: 'mode-fixture-0003', name: 'step_by_step', label: '逐步推理', max_paths: 1, description: '单路径逐步展开' },
];

export const reasoningHistory = [
  { trace_id: 'rsn-fixture-0001', task: '对比双主题下的对比度', mode: 'tree_of_thought', status: 'completed', created_at: fixedDate, duration_ms: 4210, score: 0.92 },
  { trace_id: 'rsn-fixture-0002', task: '判断 Send 按钮是否被抽屉遮挡', mode: 'self_consistency', status: 'completed', created_at: fixedDate, duration_ms: 3110, score: 0.88 },
  { trace_id: 'rsn-fixture-0003', task: '校验 aria-current 唯一性', mode: 'step_by_step', status: 'failed', created_at: fixedDate, duration_ms: 940, score: 0 },
];

export const feedbackStats = {
  total: 342,
  approval_rate: 0.87,
  up_count: 298,
  down_count: 44,
  reason_distribution: { '内容不准确': 21, '格式不符合预期': 15, '工具调用失败': 8 },
};

// ---------------------------------------------------------------------------
// Scheduler / notifications / keys / settings / auth / arcbench / permissions
// ---------------------------------------------------------------------------

export const schedulerTasks = [
  { id: 'sched-fixture-0001', name: '每日成本巡检', cron: '0 9 * * *', command: 'climber cost audit', enabled: true, last_run: fixedDate, next_run: '2026-01-16T09:00:00.000Z' },
  { id: 'sched-fixture-0002', name: '每小时健康检查', cron: '0 * * * *', command: 'climber doctor', enabled: true, last_run: fixedDate, next_run: '2026-01-15T14:00:00.000Z' },
  { id: 'sched-fixture-0003', name: '清理过期会话', cron: '30 3 * * 0', command: 'climber sessions prune', enabled: false, last_run: null, next_run: null },
];

export const apiKeys = {
  items: [
    { id: 'key-fixture-0001', provider: 'openai', name: '生产主密钥', masked_key: 'sk-...4f2a', created_at: fixedDate, last_used_at: fixedDate },
    { id: 'key-fixture-0002', provider: 'anthropic', name: '分析环境', masked_key: 'sk-ant-...9b71', created_at: fixedDate, last_used_at: null },
  ],
  total: 2,
};

export const authApiKeys = [
  { key_id: 'ak-fixture-0001', name: 'CI 发布令牌', owner: FIXTURE_USER_ID, scopes: ['tasks:write', 'skills:read'], ttl_days: 30, created_at: fixedDate, expires_at: '2026-02-14T08:30:00.000Z', last_used_at: fixedDate, revoked: false },
  { key_id: 'ak-fixture-0002', name: '只读审计', owner: FIXTURE_USER_ID, scopes: ['read'], ttl_days: null, created_at: fixedDate, expires_at: null, last_used_at: null, revoked: false },
  { key_id: 'ak-fixture-0003', name: '已吊销令牌', owner: FIXTURE_USER_ID, scopes: ['read'], ttl_days: 7, created_at: fixedDate, expires_at: '2026-01-22T08:30:00.000Z', last_used_at: null, revoked: true },
];

export const currentUser = {
  id: FIXTURE_USER_ID,
  username: 'qa-visual',
  email: 'qa-visual@climber.test',
  role: 'admin',
  created_at: fixedDate,
};

export const authHealth = { authentication_enabled: false };

export const settings = {
  autonomous_agent_mode: true,
  token_throttle_mcp_enabled: false,
  mcp_status: 'connected',
  mcp_ready: true,
  default_provider: 'openai',
  default_model: 'gpt-4o-mini',
  temperature: 0.2,
  max_tokens: 4096,
  language: 'zh-CN',
};

export const permissionConfig: PermissionConfigOut = {
  mode: 'ask',
  rules: [
    { decision: 'allow', tool: 'read_file', pattern: null, description: '只读文件无需确认' },
    { decision: 'ask', tool: 'write_file', pattern: 'src/**', description: '写入源码目录需要确认' },
    { decision: 'deny', tool: 'run_shell', pattern: 'rm *', description: '危险命令直接拒绝' },
  ],
  allowed_tools: ['read_file', 'list_files', 'grep'],
  denied_tools: ['run_shell:rm'],
};

export const arcbenchStatus: ArcBenchStatus = {
  available: true,
  message: '基准就绪',
  output_dir: '/tmp/arcbench',
  phase: 'scoring',
  phase_detail: '正在计算 120 个用例的通过率',
  trace_path: '/tmp/arcbench/trace.jsonl',
  trace_exists: true,
  acceptance: { ran: true, passed: 112, failed: 5, unverified: 3, note: '3 个用例缺少后端数据' },
  last_events: [
    { type: 'progress', timestamp: fixedDate, data: { done: 92, total: 120 } },
    { type: 'verdict', timestamp: fixedDate, data: { passed: 112 } },
  ],
  pack_artifact: '/tmp/arcbench/pack.tar.gz',
  pack_exists: true,
  updated_at: fixedDate,
};

export const healthCheck: HealthCheck = {
  status: 'ok',
  version: '0.9.14',
  database: { status: 'ok', latency_ms: 3 },
  redis: 'ok',
  chroma: 'ok',
  watchdog: { status: 'ok', restarts: 0 },
  memory: { used_mb: 412, total_mb: 2048 },
  browser_pool: { status: 'ok', size: 4 },
};

export const modelDiscovery = {
  credential_id: 'cred-fixture-0001',
  provider: 'openai',
  source: 'provider_api',
  status: 'ok',
  models: [
    { provider: 'openai', model_id: 'gpt-4o-mini', label: 'GPT-4o mini' },
    { provider: 'openai', model_id: 'gpt-4o', label: 'GPT-4o' },
  ],
};
