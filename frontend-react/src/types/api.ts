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

export interface AgentMutationResponse extends Agent {
  message?: string
}

export interface WorkflowMutationResponse extends Workflow {
  status?: string
  result?: Record<string, unknown>
}

export interface CrewMutationResponse extends Crew {
  status?: string
  result?: Record<string, unknown>
}

export interface ApiKeyMutationResponse {
  id?: string
  name?: string
  provider?: string
  base_url?: string | null
  is_active?: boolean
  message?: string
}

export interface StatsResponse {
  total_users: number
  total_agents: number
  total_sessions: number
  total_api_keys: number
  total_messages?: number
  total_tokens?: number
  total_workflows?: number
  total_crews?: number
  [key: string]: unknown
}

export interface ActionResponse {
  status?: string
  message?: string
  success?: boolean
  [key: string]: unknown
}

export interface GroupMutationResponse {
  id?: string
  name?: string
  description?: string | null
  status?: string
  message?: string
  [key: string]: unknown
}

export interface PluginMutationResponse extends Plugin {
  message?: string
  result?: Record<string, unknown>
}

export interface SettingsResponse {
  autonomous_agent_mode?: boolean
  token_throttle_mcp_enabled?: boolean
  mcp_status?: string
  mcp_ready?: boolean
  [key: string]: unknown
}

export interface SchedulerTaskResponse {
  id?: string
  name?: string
  status?: string
  schedule?: string
  [key: string]: unknown
}

export interface ReasoningTraceResponse {
  trace_id?: string
  task?: string
  answer?: string
  [key: string]: unknown
}

/** `POST /eval/run` — the persisted run summary returned by the backend. */
export interface EvaluationRunResponse {
  id: string
  dataset_id: string
  agent_id: string
  total_cases: number
  passed_cases: number
  failed_cases: number
  pass_rate: number
  average_score: number
  created_at: string
  [key: string]: unknown
}

/** One rubric item verdict inside an `EvaluationAssessResponse`. */
export interface EvaluationVerdictResponse {
  item_id: string
  passed: boolean
  reason: string
  weight: number
  [key: string]: unknown
}

/** `POST /eval/assess` — offline rubric scoring of arbitrary output. */
export interface EvaluationAssessResponse {
  scenario_id: string
  score: number
  passed: boolean
  verdicts: EvaluationVerdictResponse[]
  failure_reasons: string[]
  judge: string
  [key: string]: unknown
}

/** `POST /instruction-traces/understand` — structured instruction understanding. */
export interface InstructionUnderstandingResponse {
  raw_text?: string
  main_goal?: string | null
  constraints?: string[]
  implicit_conditions?: string[]
  ambiguities?: string[]
  confidence?: number
  clarification_questions?: string[]
  plain_language_summary?: string
  progress?: string
  candidates?: unknown[]
  context?: string | null
  [key: string]: unknown
}

export interface PermissionResolutionResponse {
  status?: string
  decision?: string
  [key: string]: unknown
}

export interface AuthKeyMutationResponse {
  status?: string
  message?: string
  revoked?: boolean
  [key: string]: unknown
}
