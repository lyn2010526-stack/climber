# Requirements Document: Architecture v2 Core

## Introduction

Build 10 architecture modules that together form the v2 core of the agent runtime: plugin kernel (lifecycle/DI/event bus), four-layer hierarchical memory, unified skill store, self-learning loop (L1/L2/L3), capability abstraction (unified routing/fallback/market), long-context management (budget/compression/RAG/prefix cache), append-only trace event log, and integration layer (event sourcing + protocol routing). All modules are master-gated by a single `ENABLE_ARCH_V2` switch.

## Glossary

- **Plugin Kernel**: Minimal kernel that does exactly three things — lifecycle management (mount/unmount with full rollback), dependency injection (service locator), and typed event bus (pub/sub + request-response).
- **Trace Log**: Append-only per-session event log (10 event types) with read/search/fork/replay/trajectory views.
- **Four-Layer Memory**: Short-term (sliding window), medium-term (task-level), long-term (MEMORY.md/USER.md freeze+diff), and FTS5 index (BM25 search).
- **Skill Store**: Three-level loading (metadata index resident, skill content on-demand, references on-demand) with usage statistics.
- **Self-Learning**: L1 (realtime fix with version history), L2 (background distillation to skill files), L3 (steward: merge/archive/optimize).
- **Capability**: Unified capability description (ID/name/type/input-output schema/cost/success rate/preconditions/side effects) with 7 adapter types and a registry that routes by `success_rate*0.5 + cost*0.3 + preference*0.2`.
- **Long Context**: Fixed 32K budget with priority-ordered trimming (tool_results > recent_turns > rag_results > history_summary > skill_index > long_term_memory), sliding window with auto-summary, compression (tool_results to single-line JSON, UI tree to interactive-only, code to diff), and prefix cache.
- **Event Sourcing**: Append-only event stream shared across multiple stores with projection rebuild and time-travel queries.

## Requirements

### Requirement 1: Master Switch and Per-Module Toggles

**User Story:** AS an operator, I want a single master switch plus per-module toggles for all v2 architecture modules, so I can enable specific modules independently.

#### Acceptance Criteria

1. WHEN master switch is OFF, NO v2 architecture module SHALL be active.
2. WHEN master switch is ON, only modules whose per-module toggle is ON SHALL be active.
3. Each module SHALL have a corresponding `enable_<module>` boolean field in Settings.
4. The Settings class SHALL provide an `is_arch_v2_active(name)` helper that checks both master and per-module.
5. `.env.example` SHALL list all v2 switches with sensible defaults (all OFF).

### Requirement 2: Plugin Kernel

**User Story:** AS a developer, I want a minimal plugin kernel so that every component (including "core" ones) can be mounted/unmounted at runtime without restart.

#### Acceptance Criteria

1. The kernel SHALL support lifecycle management: mount with dependency resolution, unmount with full rollback of all registrations (no orphan state).
2. The kernel SHALL provide dependency injection via a service locator pattern (string key -> service).
3. The kernel SHALL provide a typed event bus supporting subscribe/publish and request/response.
4. Published events SHALL be automatically forwarded to a trace sink when one is configured.
5. Unmounting a plugin SHALL reverse its service registrations, event subscriptions, and request handler registrations.
6. The kernel SHALL support cascading unmount (dependents unmounted first) and non-cascading (blocked if depended on).
7. Configuration profiles SHALL be supported (minimal/complete/offline/developer) with overrides and disabled-plugin lists.

### Requirement 3: Trace Log

**User Story:** AS a developer, I want an append-only event log that records every session action so I can debug, replay, and audit agent behavior.

#### Acceptance Criteria

1. The log SHALL be append-only (no deletion or modification of written events).
2. Each session SHALL have its own log file, rotated when it exceeds a configurable size threshold.
3. The log SHALL support 10 event types: system_prompt, reasoning, tool_call, tool_result, screenshot, decision, model_switch, subagent, context_injection, skill_load.
4. The log SHALL support read (with optional start_sequence and event_type filters), search (by content within tool_results/decisions), fork (copy events from a source session after a given sequence), replay (re-dispatch events), and trajectory (timeline summary view).

### Requirement 4: Four-Layer Memory

**User Story:** AS an agent, I need hierarchical memory so that short-term conversation, medium-term task context, and long-term learned knowledge are managed separately with appropriate retention policies.

#### Acceptance Criteria

1. Short-term memory SHALL keep a sliding window of the most recent N turns (default 10), with evicted turns available for summarization.
2. Medium-term memory SHALL organize records under task IDs, with support for finishing a task (archiving) and promoting a record to long-term.
3. Long-term memory SHALL manage MEMORY.md and USER.md files as frozen snapshots, with changes proposed as diffs that require approval before being written.
4. An FTS5 index SHALL provide BM25-ranked search over long-term memory content, with fallback to LIKE-based search when FTS5 query syntax fails.

### Requirement 5: Skill Store

**User Story:** AS an operator, I want a skill library that loads metadata eagerly and skill content lazily, with usage statistics to identify skills that need optimization.

#### Acceptance Criteria

1. The skill store SHALL load metadata index at startup (resident in memory).
2. Skill content SHALL be loaded on-demand when the skill is activated.
3. Skill references (read_reference) SHALL be loaded on-demand.
4. Each skill SHALL track usage statistics (use_count, success_count, avg_duration_ms).
5. Skills with success_rate < 60% SHALL be automatically marked as `needs_optimization`.
6. The skill market SHALL support packaging skills as .skill archive files, scanning for sensitive permissions, and importing with user authorization.

### Requirement 6: Self-Learning

**User Story:** AS an operator, I want a three-level self-learning system so that the agent automatically improves from its mistakes.

#### Acceptance Criteria

1. L1 (Realtime Fix): WHEN an error occurs, the system SHALL attempt to fix the relevant skill file, with a maximum of 3 retries, and maintain a version history for rollback.
2. L2 (Background Distillation): WHEN a complex task (>=3 operations) completes successfully, the system SHALL distill the execution trace into a skill file with name, description, trigger conditions, steps, and notes.
3. L3 (Steward): WHEN the skill library grows to >=10 skills or 7 days have passed, the steward SHALL review: merge duplicates, archive skills unused for 30 days, update stale descriptions, and generate a rollbackable report.
4. Skills with success_rate < 60% SHALL be automatically queued for L1 re-optimization.

### Requirement 7: Capability Abstraction

**User Story:** AS an agent, I want a unified capability abstraction so that any tool, MCP server, skill, HTTP endpoint, subagent, model call, or perception action is accessed through the same interface with automatic routing and fallback.

#### Acceptance Criteria

1. Each capability SHALL have a CapabilityMeta with ID, name, description, input/output JSON Schema, cost profile, success rate, preconditions, and side effects.
2. Seven adapter types SHALL be supported: LocalTool, MCP, Skill, HTTP, SubAgent, Model, Perception.
3. The registry SHALL route calls by `success_rate * 0.5 + cost * 0.3 + user_preference * 0.2` sorting.
4. On failure, the registry SHALL fall back to at most 3 alternative implementations.
5. The capability market SHALL package capabilities as .cap files, load only core 10 capabilities at startup, lazy-load the rest with LRU eviction (capacity 50).
6. Each call SHALL update success rate statistics.

### Requirement 8: Long Context

**User Story:** AS an agent, I want effective long-context management so that I can handle conversations far exceeding any single model's context window.

#### Acceptance Criteria

1. The total context budget SHALL be fixed at 32768 tokens.
2. Components SHALL be trimmed in priority order: tool_results first, then recent_turns, rag_results, history_summary, skill_index, long_term_memory last.
3. Compression SHALL be applied per-component: tool_results to single-line JSON, screenshots to VLM description (<=200 chars), UI tree to visible interactive-only nodes, code to diff, text to bullet points.
4. A sliding window SHALL keep the most recent 10 turns, with evicted turns summarized every 5 evictions.
5. A prefix cache SHALL keep the fixed prefix (system prompt + memory + skills + tools) stable across turns.
6. RAG SHALL use cosine similarity search, with sha256 fallback when no embed_fn is configured, and sqlite-vec when available.

### Requirement 9: Integration Layer

**User Story:** AS an operator, I want event sourcing and protocol routing so that state can be reconstructed from the event stream and requests can be routed by protocol.

#### Acceptance Criteria

1. The event sourcing manager SHALL manage multiple event-sourced stores sharing one event stream.
2. Each store SHALL support projection rebuild from the event stream.
3. Time-travel queries SHALL be supported (project state as of a given upto event).
4. The protocol router SHALL route requests by protocol type (http, mcp, skill, capability, file) with configurable default mappings.

### Requirement 10: Wiring and Startup

**User Story:** AS an operator, I want the v2 modules wired into the application lifecycle so that they start and stop gracefully with the app.

#### Acceptance Criteria

1. WHEN the app starts and ENABLE_ARCH_V2 is ON, the lifespan SHALL initialize all active modules.
2. When the app stops, the lifespan SHALL gracefully shut down all active v2 modules (including PluginKernel shutdown).
3. WHEN ENABLE_ARCH_V2 is OFF, no v2 module code paths SHALL be active.