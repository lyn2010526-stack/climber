# Round 9 Ledger Update

Date: 2026-09-26.

The shared `REFACTOR_50_TASKS_2026-09-26.md` file is occupied by another uncommitted workstream, so this update is additive.

## Status Changes

- Task 10: gained a concrete Workspace geometry contract test for shrinkable chat width, bounded inspector width, and compact drawer branching. Computed DOM measurements remain pending.
- Task 27: existing RightPanel tests now provide direct on-demand request assertions and session-switch cleanup evidence; browser narrow-screen drawer validation remains pending.
- Task 28: existing i18n tests remain the source of truth for runtime resource wiring; this round performed read-only review.
- Task 29: existing inspector data tests cover missing metrics, invalid metrics, session-scoped tool calls, retry, and stale-session unmount behavior; live API validation remains pending.
- Task 31: existing ChatInterface and MobileChat tests cover IME, stop, draft restoration, scroll position, and duplicate-send behavior.
- Task 33: added Markdown table overflow, fenced-code controls, and unsafe-link rejection tests.
- Task 47: static DOM contracts improved; 1440, 1280, 1024, and 390 pixel computed-width checks remain required.
- Tasks 03-08: four mature Agent source evidence records and an acceptance table were added in `ROUND9_REFERENCE_AGENT_ACCEPTANCE_2026-09-26.md`.

## Accounting Rule

Static source review and unit tests advance a task to pending-validation. A task reaches completed only after the relevant current test command, browser/API check where applicable, command, exit code, and evidence location are recorded.

No commit was created. Existing changes remain untouched.
