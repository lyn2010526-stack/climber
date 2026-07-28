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
