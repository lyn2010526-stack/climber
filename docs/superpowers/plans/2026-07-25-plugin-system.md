# Plugin & MCP System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Wire skills into agent execution, MCP servers into tool registry, build plugin lifecycle management, and create a polished plugin marketplace UI.

**Architecture:** Three-layer plugin system — (1) Plugin Manager handles install/uninstall/enable/disable with DB persistence, (2) MCP servers dynamically register tools into ToolRegistry, (3) Skills inject system prompts + tools into agent context at runtime. UI references Open WebUI/Dify design patterns with toggle cards and category grouping.

**Tech Stack:** Python/FastAPI, SQLAlchemy, React/TypeScript, TailwindCSS

**Key References:**
- Open WebUI plugin system: filter functions, pipe functions, tool wrappers
- Dify marketplace: endpoint-based extension, provider-based extension
- MCP Protocol: JSON-RPC 2.0 over stdio/SSE, tools/list, tools/call
- CrewAI: agent.tools = [tool_instances], system_prompt augmentation

---

## Task 1: Plugin Database Model & Repository

**Files:**
- Create: `app/storage/models_plugins.py`
- Modify: `app/storage/database.py` (add import)
- Create: `tests/test_plugin_models.py`

**What it does:**
- `PluginRecord` table: id, name, type (skill|mcp|prompt), source (builtin|marketplace|custom), source_url, config (JSON), status (installed|enabled|disabled|error), description, icon, category, version, installed_at, updated_at
- `PluginRepository`: CRUD + list_by_type + list_enabled + update_status

**Test:** create plugin record, update status, list by type, list enabled only.

---

## Task 2: Plugin Manager (Core Lifecycle)

**Files:**
- Create: `app/core/plugin_manager.py`
- Create: `tests/test_plugin_manager.py`

**What it does:**
- `PluginManager` singleton class
- `install(plugin_id, config)` — create DB record, load plugin instance, set status=enabled
- `uninstall(plugin_id)` — unload instance, remove DB record (builtin → just disable)
- `enable(plugin_id)` — load instance, set status=enabled
- `disable(plugin_id)` — unload instance, set status=disabled
- `get_plugin(plugin_id)` — return plugin instance
- `list_plugins(type?, status?)` — query DB
- `load_builtins()` — register all built-in skills/MCPs on startup
- For MCP plugins: manages MCPClient lifecycle (connect/disconnect)
- For Skill plugins: registers into skill_registry

**Test:** install/enable/disable/uninstall lifecycle, builtin registration, MCP client lifecycle mock.

---

## Task 3: Skills → Agent Engine Wiring

**Files:**
- Modify: `app/schemas/__init__.py` — add `skills: list[str] = []` to AgentCreate
- Modify: `app/storage/database.py` — add `skill_ids` column to Agent table
- Modify: `app/api/v1/__init__.py` — pass skills through to agent creation and session
- Modify: `app/core/agent_engine.py` — inject skill system prompts + tools in `_build_context`
- Create: `tests/test_skill_wiring.py`

**What it does:**
- `AgentCreate.skills: ["code_executor", "web_search"]` — user selects skills when creating agent
- Stored as `agent.skill_ids` in DB
- In `AgentSession.__init__`: load skill definitions, combine system prompts
- In `_build_context`: append skill system prompts to system message, add skill tools to enabled_tools
- `SkillRegistry.get_combined_prompt(skill_ids)` — concatenate skill prompts
- `SkillRegistry.get_tools_for_skills(skill_ids)` — return tool names from skills

**Test:** create agent with skills, verify system prompt includes skill prompts, verify tools are enabled.

---

## Task 4: MCP → Tool Registry Wiring

**Files:**
- Modify: `app/core/mcp.py` — add auto-registration to ToolRegistry
- Modify: `app/core/plugin_manager.py` — wire MCP install to start server + register tools
- Modify: `app/tools/__init__.py` — add `register_mcp_tool` method
- Create: `tests/test_mcp_wiring.py`

**What it does:**
- `ToolRegistry.register_mcp_tool(mcp_tool)` — wrap MCP tool as callable, register with type="mcp"
- When MCP server is installed/enabled: connect → list_tools → register each as MCP tool
- When MCP server is disabled: unregister all its tools
- MCP tool execution: calls `mcp_client.call_tool(name, args)` internally
- Track which tools belong to which MCP server for cleanup

**Test:** mock MCP client, register tools, execute tool, unregister on disable.

---

## Task 5: Built-in MCP Definitions (Real Servers)

**Files:**
- Modify: `app/skills/mcp_marketplace.py` — replace mock data with real MCP server configs
- Create: `app/skills/mcp_servers.py` — real MCP server definitions

**What it does:**
Define real MCP servers with install configs:
- `github` — `npx -y @modelcontextprotocol/server-github`
- `playwright` — `npx -y @playwright/mcp@latest`
- `filesystem` — `npx -y @modelcontextprotocol/server-filesystem`
- `sequential-thinking` — `npx @modelcontextprotocol/server-sequential-thinking`
- `memory` — `npx -y @modelcontextprotocol/server-memory`
- `context7` — `npx -y @context7/mcp`
- `docker` — `npx @docker/mcp-server`
- `sqlite` — `npx -y @modelcontextprotocol/server-sqlite`
- `fetch` — `npx -y @modelcontextprotocol/server-fetch`
- `brave-search` — `npx -y @modelcontextprotocol/server-brave-search`
- `puppeteer` — `npx -y @anthropic-ai/mcp-puppeteer`
- `postgres` — `npx -y @modelcontextprotocol/server-postgres`

Each with: name, description, command, default_env, docs_url, icon, category.

**Test:** verify all configs are valid JSON, all commands are real npm packages.

---

## Task 6: Built-in Skill Definitions (Enhanced)

**Files:**
- Modify: `app/skills/__init__.py` — update existing skills with real tool bindings
- Create: `tests/test_skill_definitions.py`

**What it does:**
Update each skill to declare which tools it needs:
- `code_executor` → tools: ["run_python", "run_bash"]
- `web_research` → tools: ["web_search", "web_scrape"]
- `code_reviewer` → tools: ["read_file", "list_files"]
- `data_analyzer` → tools: ["run_python", "read_file"]
- `task_planner` → tools: []
- `documentation_writer` → tools: ["read_file", "write_file"]
- `security_auditor` → tools: ["read_file", "run_bash"]
- `api_tester` → tools: ["http_request"]
- `database_inspector` → tools: ["run_sql"]
- `git_operator` → tools: ["run_bash"]

Each skill must have a real, non-trivial system prompt (3-5 sentences of expert persona + methodology).

**Test:** verify each skill has tools list and non-empty system prompt > 50 chars.

---

## Task 7: Plugin Marketplace API

**Files:**
- Create: `app/api/v1/plugins.py`
- Modify: `app/main.py` — add plugins router
- Create: `tests/test_plugin_api.py`

**What it does:**
- `GET /api/v1/plugins` — list all plugins with status (installed/enabled/disabled)
- `GET /api/v1/plugins/marketplace` — list available plugins from catalog
- `POST /api/v1/plugins/{id}/install` — install plugin
- `POST /api/v1/plugins/{id}/uninstall` — uninstall plugin
- `POST /api/v1/plugins/{id}/enable` — enable plugin
- `POST /api/v1/plugins/{id}/disable` — disable plugin
- `GET /api/v1/plugins/{id}/status` — get plugin status + config
- `POST /api/v1/plugins/import` — import from GitHub URL or custom config
- `GET /api/v1/plugins/categories` — list categories with counts

All endpoints require auth. Plugin operations scoped to user_id.

**Test:** each endpoint returns correct status, install/uninstall lifecycle, auth required.

---

## Task 8: Plugin Marketplace UI (Polished)

**Files:**
- Create: `frontend-react/src/pages/PluginsPage.tsx`
- Create: `frontend-react/src/components/PluginCard.tsx`
- Create: `frontend-react/src/components/PluginToggle.tsx`
- Create: `frontend-react/src/components/ImportModal.tsx`
- Modify: `frontend-react/src/App.tsx` — add Plugins nav item
- Modify: `frontend-react/src/api.ts` — add plugin API methods

**What it does:**
Full plugin marketplace page with:
- **Left sidebar**: categories (All, Skills, MCP, Prompts, Installed, Custom) with counts
- **Top bar**: search bar + "Import Plugin" button
- **Main grid**: plugin cards with icon, name, description, category badge, toggle switch
- **Plugin card states**: Not Installed (Install button), Installed/Disabled (Enable toggle), Installed/Enabled (Disable toggle with green glow)
- **Import modal**: URL input (GitHub/MCP JSON) or browse marketplace
- **Detail panel**: slide-out panel showing plugin info, config, tools, docs

Visual design references Open WebUI plugin page:
- Dark theme with subtle gradients
- Card hover effects with border glow
- Toggle switches with smooth transitions
- Category pills with color coding
- Status indicators (green=enabled, gray=disabled, amber=error)

**Test:** page renders, toggle works, install/uninstall flow, import modal opens.

---

## Task 9: Agent Creation with Plugin Selection

**Files:**
- Modify: `frontend-react/src/pages/AgentsPage.tsx` — add skill selection step
- Modify: `frontend-react/src/pages/AgentCreateModal.tsx` (or create)
- Modify: `frontend-react/src/api.ts` — add skills field to createAgent

**What it does:**
When creating/editing an agent:
- Step 1: Basic info (name, model, API key)
- Step 2: Skills selection — grid of skill cards with checkboxes, search, category filter
- Step 3: MCP tools selection — toggle which installed MCP tools are available
- Step 4: Review — show combined system prompt preview

Each step has back/next buttons. Final submit sends skills + tools to API.

**Test:** create agent with selected skills, verify API call includes skill_ids.

---

## Task 10: Final Integration & Polish

**Files:**
- Modify: `app/main.py` — ensure all routers mounted
- Modify: `app/core/plugin_manager.py` — load builtins on startup
- Modify: `app/storage/__init__.py` — include plugin tables in init_db
- Run: full test suite
- Run: frontend build

**What it does:**
- Wire PluginManager.load_builtins() into lifespan startup
- Ensure all plugin tables created in init_db
- Run full test suite — all tests pass
- Run frontend build — no errors
- Verify end-to-end: install MCP → tools appear in tool list → agent can use them

**Test:** full test suite green, frontend build clean.

---

## Execution Order

```
Task 1 (DB) → Task 2 (Plugin Manager) → Task 3 (Skills→Agent) → Task 4 (MCP→Tools)
                                                                    ↓
Task 5 (MCP Definitions) → Task 6 (Skill Definitions) → Task 7 (API) → Task 8 (UI) → Task 9 (Agent UI) → Task 10 (Integration)
```

Tasks 1-2 can run in parallel. Tasks 5-6 can run in parallel after 2. Tasks 8-9 can run in parallel after 7.
