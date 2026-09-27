# Round 8 Task 05: Dashboard And Statistics Review

- Status: read-only research; dashboard and stats pages are occupied.
- Mature source evidence: Dify `workflow/run/index.tsx:142-184` separates loading from populated panels and keeps content scrollable. This is the reference for preserving metric context during refreshes.
- Climber evidence: `DashboardPage.tsx:14-24` checks live health and distinguishes loading/online/offline; `:43-58` provides health status and quick navigation actions. `StatsPage.tsx:31-47` clears stale stats on failure and reloads through `api.getStats`; `:72-82` exposes metrics as a semantic `dl`.
- Finding: Dashboard is a health/entry page while Stats is the metric page. Stats correctly distinguishes loading, error, and unknown values; Dashboard still has user-visible hardcoded health copy that should be included in the i18n pass.
- Test: source inspection only; no full build. Targeted page tests should cover health failure, stats failure, and refresh retry.
- Risk: changing metric labels or API assumptions can invalidate existing snapshots and locale coverage.
