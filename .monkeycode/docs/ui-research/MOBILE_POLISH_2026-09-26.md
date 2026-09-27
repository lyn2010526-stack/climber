# Mobile Polish Evidence

- Date: 2026-09-26
- Scope: `AdaptiveMobileLayout`, `components/mobile`, `pages/mobile`, mobile CSS rules, mobile tests and Playwright acceptance.
- Reference evidence: existing mobile viewport and safe-area tests in `src/components/layout/__tests__/AdaptiveMobileLayout.viewport.test.tsx` and chat interaction tests in `src/components/mobile/MobileChatInterface.test.tsx`.

## Acceptance Matrix

| Viewport | Theme | Chromium checks |
| --- | --- | --- |
| 390x844 | dark/light | composer visible, 44px controls, no horizontal overflow |
| 375x812 | dark/light | draft remains after resize, send/stop target visible |
| 768x1024 | dark/light | mobile shell boundary and fallback surfaces remain usable |

## Interaction Contract

- `visualViewport.resize` and `visualViewport.scroll` clamp the fixed shell while the keyboard occludes the navigation strip.
- The composer remains in flex flow, uses a single bottom safe-area reserve, and has a higher local stacking level than the navigation strip.
- IME composition, Shift+Enter, blank drafts, rejected sends, refresh errors, stop, and retry draft restoration are covered by unit tests.
- Desktop-only mobile destinations show a named fallback card instead of rendering a compressed desktop workspace.
- The more sheet traps focus, closes on Escape/outside press, restores focus to its trigger, and uses 52px entry rows.
