import {
  Bot, Shield, Search, Wrench, Clock, Loader2, CheckCircle2,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface ClusterTask {
  id: string;
  role: string;
  description: string;
  status: string;
  dependencies: string[];
  process_type?: string;
  guardrails?: Array<{ name: string; description: string }>;
  final_output?: string;
  context?: string[];
  human_review_required?: boolean;
}

export interface AgentGroup {
  id: string;
  name: string;
  description: string;
  status: string;
  member_count: number;
  created_at: string;
  process_type?: string;
  manager_agent_id?: string;
  manager_llm?: string;
  members?: Array<{
    id: string;
    agent_id: string;
    role: string;
    status: string;
    is_worker: boolean;
    model_provider?: string;
    model_id?: string;
    tools?: string[];
    message_count?: number;
    last_active?: string;
  }>;
}

export const ROLE_ICONS: Record<string, LucideIcon> = {
  planner: Bot,
  researcher: Search,
  executor: Wrench,
  auditor: Shield,
};

export const ROLE_COLORS: Record<string, string> = {
  planner: 'bg-blue-600/10 text-blue-400 border-blue-500/20',
  researcher: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  executor: 'bg-green-500/10 text-green-400 border-green-500/20',
  auditor: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
};

export const STATUS_ICONS: Record<string, typeof Clock> = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle2,
  failed: Clock,
};

export const STATUS_COLORS: Record<string, string> = {
  pending: 'text-[var(--color-text-muted)]',
  running: 'text-blue-400',
  completed: 'text-green-400',
  failed: 'text-red-400',
};

export type ViewMode = 'cluster' | 'groups' | 'group-room' | 'collab-console';
