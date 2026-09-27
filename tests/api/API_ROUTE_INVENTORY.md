# API HTTP Route Inventory

Checked 2026-09-26 against `app.main:app` and `app.api.v1`.

## Requested Coverage

| Area | Mounted prefix | HTTP tests | Key endpoints covered |
| --- | --- | --- | --- |
| Auth | `/api/v1/auth` | `test_auth_http.py` | login, refresh, me, health, logout, password and API key paths |
| Permissions | `/api/v1/permissions` | `test_permissions_http.py` | resolve and config read/write plus auth/admin failures |
| Sessions | `/api/v1/sessions` | `test_sessions_http.py` | create, list, read, messages, clear, delete, checkpoints and resume |
| Observability emergency-stop | `/api/v1/observability/emergency-stop` | `test_observability_http.py` | status, activate, deactivate, conflicts and admin gate |
| Workflow emergency-stop | `/api/v1/workflows/{workflow_id}/run` | `test_workflows_http.py` | stored and ad-hoc runs, result and history status |
| Health/doctor | `/health`, `/api/v1/doctor` | `test_health_http.py` | component health, logs, metrics and diagnostic status |
| Reasoning | `/api/v1/reason` | `test_reasoning_http.py` | modes, sync forms, stream availability, validation, trace, feedback and history |

All tests use the real ASGI application through `httpx.AsyncClient` and
`ASGITransport`; assertions include status codes and response fields consumed by
callers.

## Router Mount Findings

- `app.main` mounts the v1 aggregate at `/api/v1` and the observability router
  separately because that router already owns the `/api/v1/observability` prefix.
- `app.api.v1` directly mounts auth, sessions, workflows, doctor, reasoning,
  permissions and the generic aggregate.
- Cost, scheduler, MCP and autonomous skills are extension routers. The
  aggregate copies only the selected source-router paths matching
  `/cost/usage`, `/scheduler/tasks`, `/mcp/servers`, `/mcp/categories`,
  `/skills/autonomous`, and the PATCH skill route. Other paths from those source
  routers are unmounted through that include mechanism; similarly named paths
  can still be supplied by the generic router.
- The websocket router is registered separately in `app.main` and does not enter
  the HTTP route aggregate.

## Silent Degradation Points

- `app.main.lifespan` logs database initialization failures and continues startup.
- Redis absence is reported as an in-process cache fallback; Telegram startup
  failures are logged and startup continues.
- The workflow executor registers an empty Crew adapter and logs a warning; Crew
  execution remains unavailable until a configured crew is supplied.
- The doctor endpoint reports subsystem failures in its payload and returns 503,
  while the general health endpoint returns 200 with `status: degraded`.
- Workflow template generation catches per-template exceptions and returns a
  reduced metadata entry, preserving a successful response.
- The reasoning `POST /reason` no-slash wrapper directly calls the slash handler
  and therefore inherits its request-time dependencies through the wrapper's
  call shape; HTTP tests cover both spellings and the unavailable-engine 503.
- Reasoning trace, feedback and history handlers resolve the caller from the
  request context, while several read endpoints do not declare an explicit
  auth dependency. This is a review point for future auth-boundary tightening.
