# Task B Inspector And ControlBar Evidence

Date: 2026-09-26. Ownership: B only. Existing `ControlBar.tsx` and `RightPanel.tsx` were read-only because they contain concurrent changes.

## Source Evidence

- `ControlBar.tsx:83-117` exposes one button per `RIGHT_PANEL_GROUPS` entry and resolves a group's active tab through `groupModel`.
- `RightPanel.tsx:76-167` renders the same group registry as expandable sections and owns section-level tabs.
- `ControlBar.tsx:174-194` retains secondary actions in one More popover, removing duplicate direct entries for snapshot, expert mode, permission mode, and autonomy.

## Decision

The current architecture has a single group entry point in the control bar and detailed navigation in the inspector. No overlapping implementation edit was made. Browser confirmation of group toggling remains pending.
