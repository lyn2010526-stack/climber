# Agent Evolution Round 2

## Focus

Absorb durable-state and session identity conventions from open-source
Agent harnesses and adapt them into the Climber SQLite checkpoint store.
The Climber event-loop was already made single-source-of-truth in round 1;
round 2 ensures the durable memory layer stops discarding the channel
snapshots that recovery needs.

## Open-Source Benchmark

- Project: OpenAI Codex item lifecycle plus DeepSeek Harness session
  checkpoint policy.
- Extracted design: durable checkpoint identifies a single session turn
  and persists every LangGraph-style channel atomically; idempotent
  upserts and write de-duplication are part of the contract.
- Source policy: official repository source only; inspiration, no copy.

## Candidates Considered

- Static candidate A, metadata JSON envelope.
  Reuses the existing `metadata_` column, formats channel snapshots as
  nested JSON, and unwraps them on read.
  Selected for the implementation because it preserves the current schema.
- Static candidate B, schema expansion.
  Adds dedicated columns for each channel field.
  Deferred because it would force a migration and the current search
  pattern reads by ID.
- Runtime Fork/Teams evidence was unavailable in this round because the
  subtask channel returned `Unauthorized: no channel is currently available`.
  The comparison above is therefore a static design comparison, not an
  independently executed A/B result.

## Implementation Summary

- `app/core/checkpoint.py` now writes and reads `channel_values`,
  `channel_versions`, `versions_seen`, and structured `pending_writes`
  through the `metadata_` column.
- `_to_checkpoint` rebuilds the typed `CheckpointData` fields from the
  envelope without leaving duplicates in `metadata`.
- `put_writes` de-duplicates by `write_id` and logs malformed entries
  rather than dropping them silently.
- `app/core/agent_engine.py` creates a fresh UUID `current_turn_id` for each
  run and uses it as the checkpoint `thread_id`.
- `_checkpoint_id` derives a deterministic UUID5 from session, turn, and
  iteration. This keeps idempotent writes within the database's 36-character
  ID contract while separating equal iterations across turns.
- Both in-memory and SQLite `get_latest` implementations now honor an
  explicitly requested `thread_id`.

## Verification

- `tests/test_checkpoint_survival.py` covers round-trip, idempotent upsert,
  write de-duplication, latest ordering, turn-scoped lookup, and stable
  cross-turn checkpoint IDs.
- `tests/test_agent_engine_edges.py` proves consecutive runs in one session
  use distinct turn and checkpoint identities.
- `tests/test_agi_p1_survival.py` continues to pass unchanged.
- `tests/test_agent_engine_edges.py` continues to pass unchanged.
- Initial red evidence:
  `_checkpoint_id` produced `sess-turns:sess-turns:1`, `current_turn_id`
  remained `None`, and both stores returned iteration 5 from an older turn
  when iteration 1 from the requested turn was expected. A follow-up review
  also showed session-wide recovery selecting an older turn solely because
  it had a higher iteration count.
- Final scoped regression:
  `75 passed in 35.62s` across checkpoint survival, AGI survival,
  Agent Engine edges, tool pipeline, and parallel concurrency suites.
- Ruff reported `All checks passed!`; Python compilation and
  `git diff --check` completed without output.

## Risks Recorded

- The de-duplication key for pending writes must remain stable across
  schema migrations; a future persistent column for `write_id` would
  strengthen the contract.
- The first implementation read the nonexistent `session.turn_id` field and
  saved `thread_id=session_id`. This was caught during self-audit before the
  round was accepted and corrected to the real `current_turn_id` lifecycle.
- SQLite accepts overlong string values despite `String(36)` declarations;
  PostgreSQL may reject them. Deterministic UUID5 IDs now enforce the shared
  length contract.

## Structured Record

`[Round 2] version v0.2.0 | checkpoint CP-20260821T160000Z-R2 | status: verified by scoped public checks | benchmark: official OpenAI Codex + DeepSeek Harness durable-state mechanisms adapted to Climber | Top3: channel snapshots dropped; pending-write dedup absent; cross-turn identity collision | candidates: static metadata envelope selected, schema expansion deferred; runtime fork blocked by unavailable channel | merged: metadata envelope, typed writes, per-run turn identity, deterministic UUID5 checkpoint identity, turn-scoped lookup, session-latest save ordering | red evidence: wrong field fallback, absent turn lifecycle, cross-turn lookup leak, stale-turn recovery ordering | final regression: 75 passed in 35.62s; Ruff, py_compile, and diff check clean | side effects: none detected in scoped verification | next: perform 7-expert cross-validation`
