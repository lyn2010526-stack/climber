// Auto-generated from FastAPI OpenAPI schema
// Climber API Client Types

export interface ApiResponse<T> {
  data?: T
  detail?: string
  type?: string
  error?: string
}

export interface Agent {
  id: string
  name: string
  provider: string
  model_id: string
  created_at?: string
}

export interface Workflow {
  id: string
  name: string
  description?: string
  nodes: any[]
  edges: any[]
  is_template?: boolean
  run_count?: number
  last_status?: string
  created_at?: string
}

export interface Crew {
  id: string
  name: string
  tasks: any[]
  created_at?: string
}

export interface Skill {
  id: string
  name: string
  description: string
  category: string
  enabled: boolean
}

export interface Plugin {
  id: string
  name: string
  description?: string
  is_enabled?: boolean
  status?: string
}

export interface Message {
  id: string
  role: string
  content: string
  created_at?: string
}

export interface Session {
  id: string
  user_id: string
  created_at?: string
}

export interface HealthCheck {
  status: string
  version: string
  database?: any
  redis?: string
  chroma?: string
  watchdog?: any
  memory?: any
  browser_pool?: any
}

export interface CreateAgentRequest {
  name: string
  provider: string
  model_id: string
}

export interface CreateWorkflowRequest {
  name: string
  nodes?: any[]
  edges?: any[]
}

export interface CreateCrewRequest {
  name: string
  tasks: any[]
}

export interface ChatRequest {
  message: string
  session_id?: string
}

export interface ToolCall {
  tool_name: string
  arguments: Record<string, any>
}

// ─── Typed response shapes for ApiClient methods ────────────────────────────

export interface SessionSummary {
  id: string
  title: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface CreateSessionResult {
  id: string
  session_id?: string
  title?: string
  status?: string
}

export interface DeleteResult {
  ok: boolean
}

export interface MessageItem {
  id: string
  role: string
  content: string | null
  tool_name?: string | null
  created_at: string
}

export interface MessagesResponse {
  messages: MessageItem[]
}

export interface AgentSummary {
  id: string
  name: string
  description: string
  provider: string
  model_id: string
  system_prompt?: string
  base_url?: string | null
  created_at?: string | null
}

export interface WorkflowSummary {
  id: string
  name: string
  description?: string
  nodes: any[]
  edges: any[]
  is_template?: boolean
  run_count?: number
  last_status?: string
  created_at?: string | null
}

export interface WorkflowTemplate {
  template_id: string
  name: string
  description?: string
  nodes?: any[]
  edges?: any[]
}

export interface TaskSummary {
  id: string
  group_id: string
  description: string
  status: string
  worker_id?: string | null
  current_round?: number
  max_rounds?: number
  total_tokens?: number
  created_at?: string
  final_output?: string
  started_at?: string
  completed_at?: string
}

export interface TaskDetail {
  id: string
  group_id: string
  description: string
  status: string
  worker_id?: string | null
  reviewer_ids?: string[]
  current_round?: number
  max_rounds?: number
  context?: any[]
  guardrails?: any[]
  human_review_required?: boolean
  human_review_status?: string
  output_schema?: Record<string, unknown>
  final_output?: string
  structured_output?: Record<string, unknown>
  total_tokens?: number
  started_at?: string
  paused_at?: string | null
  completed_at?: string
  created_at?: string
}

export interface PlatformStats {
  total_users: number
  total_agents: number
  total_api_keys: number
  total_sessions: number
  total_messages: number
  total_tokens: number
  total_workflows: number
  total_crews: number
}

export interface NotificationResult {
  ok: boolean
  error?: string
  cleared?: number
}

export interface NotificationItem {
  id?: string
  title: string
  message: string
  created_at?: string
}

export interface NotificationsResponse {
  notifications: NotificationItem[]
  total: number
}

export interface DocumentSummary {
  id: string
  name: string
  status?: string
  chunks?: number
  size?: number
}

export interface GroupMember {
  id: string
  agent_id: string
  role: string
  status: string
  is_worker: boolean
  model_provider?: string
  model_id?: string
  tools?: string[]
  message_count?: number
  last_active?: string
}

export interface GroupSummary {
  id: string
  name: string
  description: string
  topic: string
  status: string
  max_rounds: number
  process_type: string
  manager_agent_id?: string
  manager_llm?: string
  member_count: number
  members?: GroupMember[]
  created_at: string
}

export interface ToolSummary {
  name: string
  description: string
  parameters: any
}

export interface SkillSummary {
  id: string
  name: string
  description: string
  category?: string
  prompt_template?: string
  tools?: string[]
  is_enabled?: boolean
  use_count?: number
}

export interface ReasoningMode {
  id: string
  name: string
  description: string
  available: boolean
}
