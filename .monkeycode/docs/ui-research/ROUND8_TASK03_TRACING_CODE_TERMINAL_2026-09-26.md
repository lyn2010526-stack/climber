# Round 8 Task 03: Tracing, Code, And Terminal

- Status: read-only research; tracing, diff, and terminal implementation files are occupied.
- Mature source evidence: Dify `workflow/run/index.tsx:103-184` keeps Result, Detail, and Tracing in stable tabs with one independently scrolling panel and a loading layer. This supports Climber's need to preserve run context while switching views.
- Climber evidence: `TraceViewer.tsx:46-94` isolates stale detail responses with `detailRequest.current`; `:96-128` builds a parent-child span tree. `DiffPanel.tsx:37-100` parses unified hunks and tracks additions/deletions. `TerminalPanel.tsx:20-137` disposes xterm, FitAddon, observers, and resize listeners on unmount.
- Finding: lifecycle protection exists in tracing and terminal. The key remaining review item is API/session association for trace selection and explicit connection state around terminal resources.
- Test: source inspection only; no build. Candidate focused tests are existing trace/page tests plus terminal/diff tests if released by the owning agent.
- Risk: xterm and trace request cleanup are sensitive to effect dependency changes; avoid broad refactors during parallel edits.
