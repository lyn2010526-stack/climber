# Task F Chat Tool Approval DOM Evidence

Date: 2026-09-26. Ownership: F only. `ChatInterface.tsx` and `FloatingPermissionDialog.tsx` were read-only because they are occupied.

## Source Evidence

- `ChatInterface.tsx:88-116` derives pending approvals from tool calls and routes single and bulk approval callbacks.
- `FloatingPermissionDialog.tsx:51-63` guards duplicate responses and retains failed requests with an alert.
- `FloatingPermissionDialog.tsx:88-101` requires explicit confirmation for high-risk or delete actions.
- `FloatingPermissionDialog.tsx:134-156` uses a fixed responsive container, a bounded scroll region, minimized state, and a low-risk-only bulk action.

## Decision

The desktop/mobile DOM contract is represented by responsive fixed positioning, wrapping controls, and bounded content. Real approval clicks at desktop and mobile widths remain pending because the backend and approval fixture were unavailable in the live page.
