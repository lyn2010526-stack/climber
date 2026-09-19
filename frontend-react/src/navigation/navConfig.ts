import type { LucideIcon } from 'lucide-react';
import {
  MessageSquare, Bot, Network, Cpu, BarChart3,
  Sparkles, Settings, Workflow, Terminal, Key, Activity, FlaskConical, DollarSign,
  Puzzle, Package, Clock, Users, History, Bell,
} from 'lucide-react';

export type NavGroup = 'main' | 'manage' | 'config';

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
}

export const CORE_NAV_ITEMS_BASE: NavItem[] = [
  { id: 'dashboard', icon: Activity, labelKey: 'navigation.dashboard', group: 'main' },
  { id: 'chat', icon: MessageSquare, labelKey: 'navigation.chat', group: 'main', keywords: '对话 工作台' },
  { id: 'agents', icon: Bot, labelKey: 'navigation.agents', group: 'manage', keywords: '智能体 管理' },
  { id: 'workflows', icon: Workflow, labelKey: 'navigation.workflows', group: 'manage', keywords: '工作流' },
  { id: 'tasks', icon: Cpu, labelKey: 'navigation.tasks', group: 'main', keywords: '任务 监控' },
  { id: 'factory', icon: Sparkles, label: 'Factory', group: 'main', keywords: '自主 自动执行' },
  { id: 'settings', icon: Settings, labelKey: 'navigation.settings', group: 'config', keywords: '设置' },
];

export const ALL_NAV_ITEMS_BASE: NavItem[] = [
  { id: 'dashboard', icon: Activity, labelKey: 'navigation.dashboard', group: 'main', keywords: 'dashboard health status 概览' },
  { id: 'chat', icon: MessageSquare, labelKey: 'navigation.chat', group: 'main', keywords: 'home workspace dashboard 对话 工作台' },
  { id: 'factory', icon: Sparkles, label: 'Factory', group: 'main', keywords: 'auto agent execute 自主 自动执行' },
  { id: 'cluster', icon: Network, label: 'Cluster', group: 'main', keywords: 'multi agent team 集群 协作' },
  { id: 'tasks', icon: Cpu, labelKey: 'navigation.tasks', group: 'main', keywords: 'monitor task running 任务 监控' },
  { id: 'task-history', icon: History, labelKey: 'navigation.task_history', group: 'main', keywords: 'history past 历史' },
  { id: 'reasoning', icon: Activity, labelKey: 'navigation.reasoning', group: 'main', keywords: 'reason think 推理 引擎' },
  { id: 'reasoning-history', icon: History, labelKey: 'navigation.reasoning_history', group: 'main', keywords: 'reasoning history 推理历史' },
  { id: 'agents', icon: Bot, labelKey: 'navigation.agents', group: 'manage', keywords: 'agent config 智能体 管理' },
  { id: 'workflows', icon: Workflow, labelKey: 'navigation.workflows', group: 'manage', keywords: 'workflow dag 工作流' },
  { id: 'crews', icon: Users, labelKey: 'navigation.users', group: 'manage', keywords: 'crew team 团队' },
  { id: 'scheduler', icon: Clock, labelKey: 'navigation.scheduler', group: 'manage', keywords: 'cron schedule 定时' },
  { id: 'plugins', icon: Puzzle, labelKey: 'navigation.plugins', group: 'config', keywords: 'plugin marketplace 插件 市场' },
  { id: 'plugin-manage', icon: Package, labelKey: 'navigation.plugins', group: 'config', keywords: 'plugin manage installed 插件 管理' },
  { id: 'skills', icon: Package, labelKey: 'navigation.skills', group: 'config', keywords: 'skill tool 技能' },
  { id: 'notifications', icon: Bell, labelKey: 'navigation.notifications', group: 'config', keywords: 'notification alert 通知' },
  { id: 'doctor', icon: Activity, labelKey: 'navigation.monitoring', group: 'config', keywords: 'health debug 诊断 系统' },
  { id: 'mcp', icon: Terminal, labelKey: 'navigation.mcp', group: 'config', keywords: 'mcp protocol tool' },
  { id: 'apikeys', icon: Key, labelKey: 'navigation.api_keys', group: 'config', keywords: 'api key secret 密钥' },
  { id: 'stats', icon: BarChart3, labelKey: 'navigation.analytics', group: 'config', keywords: 'stats analytics chart 统计 数据' },
  { id: 'traces', icon: Activity, labelKey: 'navigation.traces', group: 'config', keywords: 'trace debug 追踪 链路' },
  { id: 'eval', icon: FlaskConical, labelKey: 'navigation.eval', group: 'config', keywords: 'eval benchmark 评估 效果' },
  { id: 'cost', icon: DollarSign, labelKey: 'navigation.costs', group: 'config', keywords: 'cost billing token 成本' },
  { id: 'settings', icon: Settings, labelKey: 'navigation.settings', group: 'config', keywords: 'settings config preference 设置' },
  { id: 'terminal', icon: Terminal, labelKey: 'navigation.terminal', group: 'config', keywords: 'terminal shell 终端' },
];

export const NAV_ITEM_IDS = new Set(ALL_NAV_ITEMS_BASE.map(item => item.id));
