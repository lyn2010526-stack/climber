import type { LucideIcon } from 'lucide-react';
import {
  MessageSquare, Bot, Network, Cpu, BarChart3,
  Factory, Brain, GitBranch, Stethoscope, Settings, Workflow, Terminal, Key, Activity, FlaskConical, DollarSign,
  Puzzle, Package, Clock, Users, History, Bell, ShieldCheck,
} from 'lucide-react';

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
  | 'tasks' | 'task-history' | 'reasoning' | 'reasoning-history' | 'terminal';

export interface NavItem {
  id: Page;
  icon: LucideIcon;
  labelKey?: string;
  label?: string;
  group?: NavGroup;
  keywords?: string;
  secondary?: boolean;
}

export const ALL_NAV_ITEMS_BASE: NavItem[] = [
  { id: 'dashboard', icon: Activity, labelKey: 'navigation.dashboard', group: 'main', keywords: 'dashboard health status 概览' },
  { id: 'chat', icon: MessageSquare, labelKey: 'navigation.chat', group: 'main', keywords: 'home workspace dashboard 对话 工作台' },
  { id: 'factory', icon: Factory, labelKey: 'navigation.factory', group: 'main', keywords: 'auto agent execute 自主 自动执行' },
  { id: 'tasks', icon: Cpu, labelKey: 'navigation.tasks', group: 'main', keywords: 'monitor task running 任务 监控' },
  { id: 'task-history', icon: History, labelKey: 'navigation.task_history', group: 'main', keywords: 'history past 历史' },
  { id: 'reasoning', icon: Brain, labelKey: 'navigation.reasoning', group: 'main', keywords: 'reason think 推理 引擎' },
  { id: 'reasoning-history', icon: History, labelKey: 'navigation.reasoning_history', group: 'main', keywords: 'reasoning history 推理历史' },
  { id: 'workflows', icon: Workflow, labelKey: 'navigation.workflows', group: 'main', keywords: 'workflow dag 工作流' },
  { id: 'scheduler', icon: Clock, labelKey: 'navigation.scheduler', group: 'main', keywords: 'cron schedule 定时' },
  { id: 'terminal', icon: Terminal, labelKey: 'navigation.terminal', group: 'main', keywords: 'terminal shell 终端' },
  { id: 'cluster', icon: Network, labelKey: 'navigation.cluster', group: 'main', secondary: true, keywords: 'multi agent team 集群 协作' },
  { id: 'crews', icon: Users, labelKey: 'navigation.crews', group: 'main', secondary: true, keywords: 'crew team 团队 协作' },
  { id: 'agents', icon: Bot, labelKey: 'navigation.agents', group: 'manage', keywords: 'agent config 智能体 管理' },
  { id: 'skills', icon: Package, labelKey: 'navigation.skills', group: 'manage', keywords: 'skill tool 技能' },
  { id: 'mcp', icon: Terminal, labelKey: 'navigation.mcp', group: 'manage', keywords: 'mcp protocol tool' },
  { id: 'plugins', icon: Puzzle, labelKey: 'navigation.plugins', group: 'manage', keywords: 'plugin marketplace 插件 市场' },
  { id: 'plugin-manage', icon: Package, labelKey: 'navigation.plugin_management', group: 'manage', keywords: 'plugin manage installed 插件 管理' },
  { id: 'notifications', icon: Bell, labelKey: 'navigation.notifications', group: 'config', keywords: 'notification alert 通知' },
  { id: 'doctor', icon: Stethoscope, labelKey: 'navigation.monitoring', group: 'config', keywords: 'health debug 诊断 系统' },
  { id: 'apikeys', icon: Key, labelKey: 'navigation.api_keys', group: 'config', keywords: 'api key secret 密钥' },
  { id: 'authapikeys', icon: ShieldCheck, labelKey: 'apiKeys.authApiKeys.create_new', group: 'config', keywords: 'auth access token API 访问密钥 授权' },
  { id: 'stats', icon: BarChart3, labelKey: 'navigation.analytics', group: 'config', keywords: 'stats analytics chart 统计 数据' },
  { id: 'traces', icon: GitBranch, labelKey: 'navigation.traces', group: 'config', keywords: 'trace debug 追踪 链路' },
  { id: 'eval', icon: FlaskConical, labelKey: 'navigation.eval', group: 'config', keywords: 'eval benchmark 评估 效果' },
  { id: 'cost', icon: DollarSign, labelKey: 'navigation.costs', group: 'config', keywords: 'cost billing token 成本' },
  { id: 'settings', icon: Settings, labelKey: 'navigation.settings', group: 'config', keywords: 'settings config preference 设置' },
];

export const CORE_NAV_ITEMS_BASE = ALL_NAV_ITEMS_BASE.filter(item =>
  (['dashboard', 'chat', 'agents', 'workflows', 'tasks', 'factory', 'apikeys', 'settings'] as Page[]).includes(item.id),
);

export const NAV_ITEM_IDS = new Set(ALL_NAV_ITEMS_BASE.map(item => item.id));

// Mobile keeps the conversation shell and compact operational views. Dense
// editors, traces, terminals and settings remain desktop-first and fall back
// to the mobile chat entry instead of rendering an unusable desktop surface.
export const MOBILE_ADAPTED_PAGE_IDS: ReadonlySet<Page> = new Set<Page>([
  'dashboard', 'chat', 'factory', 'tasks', 'agents', 'cluster', 'crews', 'apikeys', 'authapikeys', 'settings',
]);
