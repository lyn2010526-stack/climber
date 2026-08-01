# Climber Architecture

## Overview

Climber is a local-first AI Agent platform designed for autonomous software development.

## Design Principles

1. **Local-first** — No cloud dependency, all data on user's machine
2. **Layered architecture** — Clear separation of concerns
3. **Type-safe** — Typed messages and structured data throughout
4. **Extensible** — Plugin system for tools, MCP for external integration
5. **Observable** — Structured logging, metrics, and tracing
6. **Safe** — Permission tiers, sandbox mode, input sanitization

## Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│ Presentation Layer                                   │
│  - React Frontend (Vite + TypeScript)                │
│  - REST API (FastAPI)                                │
│  - SSE Event Streaming                               │
├─────────────────────────────────────────────────────┤
│ Agent Layer                                          │
│  - AgentEngine (main orchestrator)                   │
│  - MultiAgentOrchestrator (fork/coordinate/team)     │
│  - HierarchicalCrew (planner→worker→reviewer)        │
├─────────────────────────────────────────────────────┤
│ Core Services Layer                                  │
│  - ContextManager (5-layer pipeline)                 │
│  - ToolRuntime (unified execution)                   │
│  - PermissionController (7-tier permissions)         │
│  - ModelScheduler (intelligent selection)            │
│  - SessionManager (checkpoint/resume/fork)           │
├─────────────────────────────────────────────────────┤
│ Infrastructure Layer                                 │
│  - SQLite / PostgreSQL (SQLAlchemy)                  │
│  - ChromaDB (vector memory)                          │
│  - MCP Client (external tools)                       │
│  - LLM Provider Interface (multi-provider)           │
└─────────────────────────────────────────────────────┘
```

## Data Flow

### Chat Request Flow
1. User sends message via REST API
2. AgentEngine creates/reuses session
3. ContextManager assembles context (5 layers)
4. ModelScheduler selects optimal model
5. LLM generates response (possibly with tool calls)
6. PermissionController checks each tool call
7. ToolRuntime executes approved tools
8. Results streamed back via SSE

### Multi-Agent Flow
1. Planner decomposes task into subtasks
2. Coordinator dispatches to workers in parallel
3. Reviewer validates each worker's output
4. DeadlockDetector monitors for stagnation
5. ConflictArbitrator resolves disagreements

## Key Components

### Context Management
- **L0**: Immutable base rules
- **L1**: Project rules (CLAUDE.md)
- **L2**: Session context (persona, role)
- **L3**: Progress/plan (PLAN.md)
- **L4**: Memory injection (episodic, core)

### Tool System
- **ToolRuntime**: Unified execution surface
- **MCPBridge**: Auto-registers MCP server tools
- **Security**: Path validation, shell analysis, sandbox

### Model Scheduling
- **Scoring**: cost × speed × quality
- **Circuit Breaker**: Failover after threshold
- **Fallback Chain**: Ordered provider list

## Security Model

| Level | Description |
|-------|-------------|
| Read-Only | Only read operations |
| Standard | Read + safe writes |
| Accept Edits | Auto-accept modifications |
| Plan | Exploration only |
| Auto | Full autonomous |
| Manual | Ask for every write |
| Bypass | Skip all checks |

## Observability

- **Logging**: structlog JSON format with correlation IDs
- **Metrics**: Session/token/latency tracking
- **Tracing**: Per-request correlation across async boundaries
- **Health**: /health endpoint for monitoring
