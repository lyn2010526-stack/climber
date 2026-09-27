# Task C Session Sidebar Information Architecture

Date: 2026-09-26. Ownership: C only. `SessionSidebar.tsx` was read-only because it is occupied by another workstream.

## Source Evidence

- `SessionSidebar.tsx:182-239` places new-session creation and its configuration disclosure before identity and list state.
- `SessionSidebar.tsx:252-320` gives the session list a labelled heading, count, loading status, empty state, semantic list items, current-session marker, and per-row deletion control.
- `SessionSidebar.tsx:322-350` keeps checkpoint history as a separate, explicitly controlled region below the session list.

## Decision

The final information architecture is `create -> creation options -> session list -> checkpoint history -> user switcher`. Static evidence is complete; creation and checkpoint behavior with live API data remain pending.
