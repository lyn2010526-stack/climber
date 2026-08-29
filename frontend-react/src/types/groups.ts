import type { JsonObject, OkResult } from './common';
import type { GroupMember, GroupSummary } from './api';

export interface CreateGroupInput {
  name: string;
  description?: string;
  topic?: string;
  status?: string;
  max_rounds?: number;
  process_type?: 'sequential' | 'hierarchical' | 'group_chat';
  template?: 'default';
}

export interface AddGroupMemberInput {
  agent_id: string;
  role?: string;
  model_provider?: string;
  model_id?: string;
  api_key?: string;
  api_key_encrypted?: string;
  tools?: string[];
  is_worker?: boolean;
}

export interface AddedGroupMember extends Pick<GroupMember, 'id' | 'agent_id' | 'role' | 'status' | 'is_worker'> {
  group_id: string;
}

export interface GroupMessage {
  id: string;
  sender_id: string;
  agent_id: string | null;
  sender_name: string;
  content: string;
  message_type: string;
  created_at: string;
}

export interface GroupMessagesResponse {
  messages: GroupMessage[];
}

export interface RemoveGroupMemberResult extends OkResult {
  deleted: string;
}

export interface ClusterPlanTask {
  id?: string;
  role?: string;
  description?: string;
  task?: string;
  status?: string;
  dependencies?: string[];
  process_type?: string;
  guardrails?: JsonObject[];
  context?: string[];
  human_review_required?: boolean;
}

export interface ClusterProgress {
  total: number;
  completed: number;
  failed: number;
  running: number;
  pending: number;
  progress_pct: number;
}

export interface ClusterCreateResult {
  id: string;
  name: string;
  endpoint: string;
  status: string;
  plan?: ClusterPlanTask[];
  progress?: ClusterProgress;
}

export interface ClusterStatusNode {
  id: string;
  name: string;
  status: string;
  role: string;
}

export interface ClusterStatus {
  status: string;
  total_nodes: number;
  online_nodes: number;
  nodes: ClusterStatusNode[];
  plan?: ClusterPlanTask[];
}

export type CreatedGroup = GroupSummary;
