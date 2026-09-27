# Right Panel Polish Acceptance

- Date: 2026-09-26
- Browser: Chromium via Playwright
- Preview: `https://5173-df600483e58dab88.monkeycode-ai.online`

## Viewports

| Viewport | Result | Evidence |
| --- | --- | --- |
| 1024 x 768 | Inspected | Compact drawer stays in layout flow; chat remains available beside it; Escape closes the drawer. |
| 768 x 1024 | Inspected | Compact drawer uses bounded width and does not overlay the composer/send region. The existing mobile-project selector check fails at this width because it expects the mobile send contract. |
| 390 x 844 | Pass | Mobile composer and send controls remain reachable; existing mobile overlap checks pass. |

## Interaction Results

- Right inspector exposes 7 tabs across 4 groups and mounts only the active section.
- Section lazy loading shows a stable loading skeleton; section failures expose retry through the error state.
- Group expansion and selected tabs persist per session context in local storage.
- External tab requests use the store nonce and are consumed once.
- Compact drawer supports header close, Escape dismissal, and focus recovery to the ControlBar inspector toggle.
- ControlBar keeps pause, stop, snapshot, rollback, inspector toggle, expert mode, and permission controls. Tab navigation remains inside the inspector.
- Backend-reported counts are the only counts displayed; loading, failed, and unknown values remain unreported.

## Verification

- Focused tests: 6 files, 63 tests passed.
- Typecheck: the inspector boundary compiles after the final change; the repository check remains blocked by an existing `SessionSidebar.tsx:373` `focus` type error outside the allowed edit scope.
- Chromium viewport coverage was performed at 1024, 768, and 390 CSS pixels. The repository's dedicated mobile polish suite reports 5 of 6 checks passed; the 768px mobile send-selector check remains failing because that viewport uses the mobile project route contract.
