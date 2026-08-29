# Round 3 Seven-Expert Cross Audit

## Scope

- Date: 2026-08-22
- Mode: seven parallel read-only expert reviews
- Shared database tests: not executed by experts
- Files modified by experts: none
- Main-session checkpoint: `CP-20260822T062500Z-R4`

## Scores

| Dimension | Score | Highest-Priority Finding |
|---|---:|---|
| Cognition | 57 | Context compression lacks semantic-preservation evidence and unfamiliar-domain held-out tests. |
| Tools | 66 | Duplicate tool-call IDs can repeat side effects; recovery can bypass the normal execution boundary. |
| Memory | 46 | Agent Engine defaults to an in-memory checkpoint store; replay is process-local. |
| Reasoning | 56 | The main loop lacks a shared wall-clock, token, retry, and tool-attempt budget. |
| Collaboration | 68 | Hierarchical completion has a weaker fencing path and same-level DAG execution is serial. |
| Security | 76 | Authentication is a fixed local identity and the command sandbox lacks strong OS-level isolation. |
| Open-source benchmarking | 73 | Round 2 and 3 source attribution needs clearer separation between upstream mechanisms and Climber extensions. |

Arithmetic mean: `63.1/100`.

## Security Stop Gate

The security score is below the required threshold of 90. Round 4 feature,
memory, reasoning, collaboration, and MCP work is paused until a scoped human
decision is recorded.

Proposed low-risk security scope for human approval:

1. Replace string-prefix path containment checks with resolved path ancestry
   checks and add temporary-directory tests for sibling-prefix and symlink
   escape cases.
2. Restrict the permission configuration API from selecting `bypass`, type
   the request with the existing permission enum, and prove explicit deny
   rules remain effective in AUTO mode.

The following remain outside the proposed scope:

- MCP registration changes.
- New high-risk tools.
- Sandbox rule expansion.
- Authentication architecture replacement.
- OS/container isolation architecture.

## Consolidated Priority Queue

1. Security: close path containment and API-level BYPASS exposure after human approval.
2. Memory: connect the production Agent Engine to durable checkpoint storage and prove independent-process recovery.
3. Tools: add a turn-local tool-call ledger for duplicate-ID idempotency and conflict detection.
4. Reasoning: add a shared turn budget for deadline, model attempts, tool attempts, and token consumption.
5. Cognition: add semantic-preservation contracts for context compression and unfamiliar-domain held-out tests.
6. Collaboration: unify fencing checks and enforce same-group handoff.
7. Open-source evidence: pin upstream SHAs and separate upstream mechanisms from Climber-native extensions.

## Extreme End-to-End Audit Themes

- Unfamiliar synthetic-domain reasoning across compression, disconnect, and restart.
- Duplicate side-effecting tool calls plus recovery and cancellation.
- Cross-process checkpoint, replay, and long-term-memory recovery.
- Budgeted model fallback with evidence-linked final claims.
- Five-agent lease takeover, rejection, timeout, and deterministic merge.
- Two-user approval, replay ownership, and path-boundary enforcement.
- Semantic checkpoint and idempotent side-effect recovery based on pinned upstream modules.

## Evidence Limits

- Expert reviews were static and read-only.
- Runtime Teams/Fork isolation was represented by seven independent task
  contexts; no subagent modified or merged code.
- The security expert's category table used a nonstandard evidence bonus; the
  final score remains below 90 under both the expert's stated result and a
  normalized interpretation.
- No claim is made that the terminal stopping criteria are met.
