# Frontend API Boundary

This document defines the single architecture rule for how the React frontend
talks to the backend. It applies to every file under `src/`.

## The Rule

**Components, hooks, stores and pages must never call `fetch`, `EventSource`,
`WebSocket`, or build a backend URL themselves.** Every backend interaction —
request, SSE stream, WebSocket, slash command, cancel — goes through the
facade in `src/api.ts` (`import { api } from '../api'`).

The only files allowed to touch `fetch` directly are:

- `src/api.ts` — the facade. It owns base-URL composition, auth headers,
  the 401 → refresh-token → retry loop, error normalisation
  (`ApiRequestError`) and all SSE/WS channel helpers.
- `src/lib/api-client.ts` — the low-level client that `src/api.ts` builds on.
  It exports `API_BASE_URL`, `getAuthHeaders` and a generic `apiClient`
  transport. It exists for the facade and for legacy modules that were wired
  before the facade grew SSE support; new code must not import it.

If a component needs an endpoint that `api.ts` does not expose yet, do **not**
add a `fetch` call next to the component. Add a method to `ApiClient` in
`src/api.ts` and have the component call it.

## Why a single boundary

- Auth lives in one place: bearer token injection, the refresh-retry loop and
  the "Authentication required" failure all happen inside `ApiClient.request`.
  A stray `fetch` silently skips token refresh and produces errors the rest of
  the app never makes.
- Error handling is uniform: non-2xx answers become `ApiRequestError` with the
  backend's `detail`, FastAPI 422 arrays are flattened, and callers can rely
  on `status` (409 approval-expired, 401 auth, 429 rate-limit).
- URL composition is testable: every path joins `API_BASE_URL` ('/api/v1') in
  the facade, so the Vite dev proxy and production rewrite stay in sync and
  contract tests can assert full URLs.

## Adding a new endpoint

1. Add a method to the `ApiClient` class in `src/api.ts`. Use
   `this.request<T>(path, init)` for JSON bodies; it handles auth and the
   refresh loop.
2. Declare the response shape as an exported `interface` next to the other
   endpoint types at the top of `src/api.ts` (see `SessionListItem`,
   `ClusterStatusOut`, `CostUsageOut` for the pattern). Avoid `any`.
3. Call the method from the component. Components stay typed and free of URL
   strings.

## SSE and WebSocket channels

Streaming endpoints cannot go through `request` because the body must be
consumed incrementally. The facade still owns them; the direct `fetch` calls
that power them are implementation details of the facade, not an invitation to
spread them:

- `api.chatStream / api.startSessionInputs` — chat and steering SSE
  (consumed by `useChat`; the stream contract is covered by tests — do not
  change frame handling casually).
- `api.runSlashCommand` — slash-command SSE (`/sessions/{id}/slash`).
- `api.cancelSessionTurn` — fire-and-forget turn interrupt.
- `api.streamTaskEvents(taskId, signal)` — returns the raw `Response` so the
  caller can own idle-timeout, Retry-After and frame validation; URL and auth
  headers stay centralised.
- `api.openGroupWebSocket(groupId)` — group hub WS; the browser WebSocket
  handshake cannot ride the fetch proxy, so the URL is derived from the page
  origin inside the facade.
- `api.listChatCommands()` — public catalog read (no auth header by design).

## Legacy transport users (do not grow this list)

`apiClient` from `src/lib/api-client.ts` is used directly by a few modules
(`SessionSidebar` identity probes, `AnchoredLeftNav`). They predate the
facade's current surface and lack automatic token refresh; prefer `api.ts`
for anything new and migrate these callers when touching them anyway.

## Review checklist

A diff violates the boundary when it:

- adds `fetch(`, `new WebSocket(`, or `new EventSource(` outside `src/api.ts`
  and `src/lib/api-client.ts` (test doubles excluded);
- hardcodes '/api/v1' or a backend origin anywhere outside those two files;
- reads `API_BASE_URL` or `getAuthHeaders` outside the facade to build its own
  request;
- adds a new endpoint by widening an existing method's `any` return instead
  of declaring the response interface.
