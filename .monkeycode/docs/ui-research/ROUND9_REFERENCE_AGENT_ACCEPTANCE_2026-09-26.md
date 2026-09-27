# Mature Agent Reference Evidence And Acceptance Table

Date: 2026-09-26. Evidence is from local read-only repositories under `/tmp/opencode/ref-repos`.

| Project and revision | Source evidence | Contract extracted | Climber acceptance mapping |
| --- | --- | --- | --- |
| assistant-ui / `5df393f0bbd84cd2a73731d60d2e973d991cbd27` | `packages/ui/src/components/react/assistant-ui/elements/thread-list.tsx:8-99` | Thread data carries title, time and unread state; active row uses `aria-current`; selection is a button; long titles truncate; hover actions are supplemental | SessionSidebar must retain semantic current-session state, readable metadata, and a keyboard-usable primary row. |
| OpenHands / local HEAD | `src/components/features/conversation/conversation-main/conversation-mobile-panel-page.tsx:13-70` | Mobile inspector has an explicit back action, compact tab header, layout-preserving flex min-height rules, and effect cleanup when leaving the panel | RightPanel compact drawer needs a reachable close/back path and cleanup when hidden; map to tasks 27, 30 and 47. |
| Cline / local HEAD | `apps/vscode/webview-ui/src/components/chat/ChatTextArea.tsx` and `ChatTextArea.test.tsx` | Dedicated composer component and focused behavior tests provide a stable seam for input, keyboard and send-state contracts | ChatInterface and MobileChat must keep IME, submit, draft and stop behavior independently testable; map to tasks 31-33. |
| Dify / local HEAD | `web/app/components/base/chat/chat/answer/index.tsx:79-129,144-158` | Agent reasoning is derived from actual content/finish fields; empty persisted reasoning objects are ignored; ResizeObserver recalculates content widths; response completion has explicit signals | Markdown/message state must distinguish empty, streaming and completed data; Workspace width checks must observe real container changes; map to tasks 10, 29, 33 and 47. |

## Acceptance Table

| Contract | Required evidence | Current Climber evidence | Decision |
| --- | --- | --- | --- |
| Session identity | active row, stable title/time, current marker | `SessionSidebar.tsx`, `SessionSidebar.accessibility.test.tsx` | Preserve semantic row and add runtime viewport validation |
| Mobile panel navigation | back/close path and unmount cleanup | `WorkspaceLayout.tsx:72-79`, OpenHands mobile panel evidence | Drawer geometry is present; close affordance requires browser interaction check |
| Composer states | IME, blank, pending, stop, failure draft | `MobileChatInterface.test.tsx`, `ChatInterface.task03.test.tsx` | Existing behavior coverage is substantive; run current suite |
| Reasoning truth | content/finish fields, empty object handling | `ChatInterface.tsx:88-102`, Dify evidence | Avoid inferred progress and synthetic metrics |
| Responsive width | shrinkable main column, bounded inspector, table/code local overflow | `WorkspaceLayout.geometry.task01.test.tsx`, `MarkdownRenderer.states.task03.test.tsx` | Static contracts added; computed DOM widths remain required |

No external source code, icons, brand assets, or licenses were copied into the application.
