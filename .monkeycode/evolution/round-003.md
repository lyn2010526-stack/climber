# Agent Evolution Round 3

## Focus

Adapt bounded event replay from the verified OpenAI Codex thread event buffer
and per-session replay isolation from DeepSeek Harness into Climber's native
AgentSession and protected chat API.

## Benchmark And Candidates

- Baseline before this round: backend focused suites `50 passed in 23.42s`;
  frontend `useChat` suite `9 passed in 5.97s`.
- Candidate A, checkpoint-only recovery: smallest change, but an SSE gap has
  no event source for replay.
- Candidate B, in-memory bounded replay buffer: selected and implemented;
  supports monotonic cursors, capacity/byte eviction, payload copies, and
  turn filtering without schema migration.
- Candidate C, persistent event table: deferred because it requires schema,
  migration, writer, and cleanup changes beyond this round's low-risk scope.
- Runtime Fork/A-B execution remained unavailable because the subtask channel
  returned `Unauthorized: no channel is currently available`; comparison is
  labeled static and the selected candidate was verified locally.

## Implementation

- Added `EventReplayBuffer` with a 256-event and 256 KiB default budget.
- Added monotonic `sequence`, stable in-process `event_id`, and `turn_id` to
  `ReplayRecord`.
- Recorded emitted Agent Engine events after `_run_locked` produces them,
  preserving the existing SSE payload contract.
- Added authenticated `GET /api/v1/chat/{session_id}/chat/replay` with bounded
  `after`, `turn_id`, and `limit` query parameters plus cursor metadata.
- Enforced session ownership in the replay endpoint.
- Added unit, integration, cross-turn isolation, capacity, byte-budget,
  deep-copy, cursor, authorization, and unknown-session tests.

## Verification

- Backend scoped regression: `91 passed in 43.22s`.
- Frontend `useChat` regression: `9 passed in 5.48s`.
- Ruff: passed for all round-3 Python files.
- Python compilation: passed.
- Frontend `npm run lint`: passed.
- Frontend `npm run build`: passed; Vite built 2784 modules in 3.04s.
- `git diff --check`: passed.

## Risks And Limits

- The buffer is process-local and bounded. Restart or multi-worker deployment
  loses retained events; persistent replay is a future candidate.
- A cursor older than the retained window receives the retained suffix and the
  response exposes `oldest_sequence` so callers can detect a replay gap.
- No permission, MCP registration, high-risk tool, or sandbox rule changed.
- The mixed worktree contains substantial pre-existing changes; this round's
  files are recorded without resetting or committing unrelated work.

## Structured Record

`[Round 3] version v0.3.0 | checkpoint CP-20260822T032500Z-R3 plus closeout checkpoint | status: locally verified | benchmark: OpenAI Codex bounded event buffer + DeepSeek Harness per-turn replay isolation | Top3: no replay source after SSE gap; no event sequence; possible cross-turn leakage | selected: bounded in-memory replay with turn filter and protected API | runtime fork: unavailable | final regression: 91 passed in 43.22s; frontend 9 passed in 5.48s; lint, build, compile, Ruff and diff check clean | side effects: none detected in scoped verification | residual: process-local durability | next: consider persistent event storage only after human-approved schema scope`
