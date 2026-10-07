import type { NavigationIconName } from '../lib/icons';

export type NavGroup = 'main' | 'manage' | 'config';

export const NAV_GROUPS = [
  { id: 'main', label: '工作' },
  { id: 'manage', label: '资源' },
  { id: 'config', label: '管理运维' },
] as const satisfies readonly { id: NavGroup; label: string }[];

export type Page =
  | 'dashboard' | 'chat' | 'agents' | 'workflows' | 'crews' | 'apikeys' | 'authapikeys'
  | 'skills' | 'notifications' | 'doctor' | 'mcp' | 'stats' | 'factory' | 'plugins'
  | 'scheduler' | 'cluster' | 'traces' | 'eval' | 'cost' | 'plugin-manage' | 'settings'
  | 'tasks' | 'task-history' | 'reasoning' | 'reasoning-history' | 'terminal' | 'audit' | 'prompt-templates' | 'documents'
  | 'integrations' | 'security';

export interface NavItem {
  id: Page;
  icon: NavigationIconName;
  labelKey?: string;
  label?: string;
  group?: NavGroup;
  keywords?: string;
  secondary?: boolean;
}

export const ALL_NAV_ITEMS_BASE: NavItem[] = [
  { id: 'dashboard', icon: 'activity', labelKey: 'navigation.dashboard', group: 'main', keywords: 'dashboard health status 概览' },
  { id: 'chat', icon: 'conversation', labelKey: 'navigation.chat', group: 'main', keywords: 'home workspace dashboard 对话 工作台' },
  { id: 'factory', icon: 'factory', labelKey: 'navigation.factory', group: 'main', keywords: 'auto agent execute 自主 自动执行' },
  { id: 'tasks', icon: 'task', labelKey: 'navigation.tasks', group: 'main', keywords: 'monitor task running 任务 监控' },
  { id: 'task-history', icon: 'history', labelKey: 'navigation.task_history', group: 'main', keywords: 'history past 历史' },
  { id: 'reasoning', icon: 'reasoning', labelKey: 'navigation.reasoning', group: 'main', keywords: 'reason think 推理 引擎' },
  { id: 'reasoning-history', icon: 'history', labelKey: 'navigation.reasoning_history', group: 'main', keywords: 'reasoning history 推理历史' },
  { id: 'workflows', icon: 'workflow', labelKey: 'navigation.workflows', group: 'main', keywords: 'workflow dag 工作流' },
  { id: 'scheduler', icon: 'clock', labelKey: 'navigation.scheduler', group: 'main', keywords: 'cron schedule 定时' },
  { id: 'terminal', icon: 'terminal', labelKey: 'navigation.terminal', group: 'main', keywords: 'terminal shell 终端' },
  { id: 'cluster', icon: 'network', labelKey: 'navigation.cluster', group: 'main', secondary: true, keywords: 'multi agent team 集群 协作' },
  { id: 'crews', icon: 'members', labelKey: 'navigation.crews', group: 'main', secondary: true, keywords: 'crew team 团队 协作' },
  { id: 'agents', icon: 'agent', labelKey: 'navigation.agents', group: 'manage', keywords: 'agent config 智能体 管理' },
  { id: 'skills', icon: 'skills', labelKey: 'navigation.skills', group: 'manage', keywords: 'skill tool 技能' },
  { id: 'mcp', icon: 'tool', labelKey: 'navigation.mcp', group: 'manage', keywords: 'mcp protocol tool' },
  { id: 'plugins', icon: 'plugins', labelKey: 'navigation.plugins', group: 'manage', keywords: 'plugin marketplace 插件 市场' },
  { id: 'plugin-manage', icon: 'skills', labelKey: 'navigation.plugin_management', group: 'manage', keywords: 'plugin manage installed 插件 管理' },
  { id: 'prompt-templates', icon: 'file', labelKey: 'navigation.prompt_templates', group: 'manage', keywords: 'prompt template 提示词 模板' },
  { id: 'documents', icon: 'file', labelKey: 'navigation.documents', group: 'manage', keywords: 'document knowledge rag 文档 检索' },
  { id: 'notifications', icon: 'notification', labelKey: 'navigation.notifications', group: 'config', keywords: 'notification alert 通知' },
  { id: 'doctor', icon: 'doctor', labelKey: 'navigation.monitoring', group: 'config', keywords: 'health debug 诊断 系统' },
  { id: 'apikeys', icon: 'key', labelKey: 'navigation.api_keys', group: 'config', keywords: 'api key secret 密钥' },
  { id: 'authapikeys', icon: 'auth', labelKey: 'apiKeys.authApiKeys.create_new', group: 'config', keywords: 'auth access token API 访问密钥 授权' },
  { id: 'stats', icon: 'chart', labelKey: 'navigation.analytics', group: 'config', keywords: 'stats analytics chart 统计 数据' },
  { id: 'traces', icon: 'trace', labelKey: 'navigation.traces', group: 'config', keywords: 'trace debug 追踪 链路' },
  { id: 'audit', icon: 'audit', labelKey: 'navigation.audit', group: 'config', keywords: 'audit log observability 审计 日志' },
  { id: 'integrations', icon: 'integrations', labelKey: 'navigation.integrations', group: 'config', keywords: 'integration qqbot langgraph mem0 agent 集成' },
  { id: 'security', icon: 'security', labelKey: 'navigation.security', group: 'config', keywords: 'security policy quota allowlist 安全 策略 配额 白名单' },
  { id: 'eval', icon: 'eval', labelKey: 'navigation.eval', group: 'config', keywords: 'eval benchmark 评估 效果' },
  { id: 'cost', icon: 'cost', labelKey: 'navigation.costs', group: 'config', keywords: 'cost billing token 成本' },
  { id: 'settings', icon: 'settings', labelKey: 'navigation.settings', group: 'config', keywords: 'settings config preference 设置' },
];

export const CORE_NAV_ITEMS_BASE = ALL_NAV_ITEMS_BASE.filter(item =>
  (['dashboard', 'chat', 'agents', 'workflows', 'tasks', 'factory', 'apikeys', 'settings'] as Page[]).includes(item.id),
);

export const NAV_ITEM_IDS = new Set(ALL_NAV_ITEMS_BASE.map(item => item.id));

// Mobile keeps the conversation shell and compact operational views. Dense
// editors, traces, terminals and settings remain desktop-first and fall back
// to the mobile chat entry instead of rendering an unusable desktop surface.
export const MOBILE_ADAPTED_PAGE_IDS: ReadonlySet<Page> = new Set<Page>([
  'dashboard', 'chat', 'factory', 'tasks', 'agents', 'cluster', 'apikeys', 'authapikeys', 'settings',
]);
