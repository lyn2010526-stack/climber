# Design System Polish: 2026-09-26

## Scope

This note records the shared visual and accessibility baseline for the Climber
Agent workspace. The implementation scope is limited to shared tokens, shared UI
primitives, shell navigation, and accessibility verification.

## Reference Patterns

- Dify `packages/dify-ui` treats primitives as stable boundaries with semantic
  HTML, design tokens, accessible-name contracts, and focused tests.
- Dify's overlay guidance keeps focus ownership, portal lifecycle, layering, and
  dismissal behavior in the dialog or menu primitive.
- Vercel Labs Web Interface Guidelines require keyboard-complete interactions,
  visible `:focus-visible` treatment, focus movement and restoration for
  overlays, 44px mobile targets, redundant status cues, and icon-only labels.

Sources:

- https://github.com/langgenius/dify/tree/main/packages/dify-ui
- https://github.com/vercel-labs/web-interface-guidelines

## Applied Baseline

- Neutral slate surfaces use one page canvas, four surface steps, and semantic
  accent, border, focus, success, warning, error, and info tokens.
- Primary and secondary text colors are tuned above the 4.5:1 text threshold in
  both themes. Control boundaries use the stronger border tokens for the 3:1
  non-text boundary target.
- Shared controls use 32px to 44px density steps, with the app shell and mobile
  controls retaining a 44px touch target. The mobile content and main layout
  continue to reserve `--mobile-nav-reserve`.
- Focus is visible through a two-pixel accent outline and page-colored offset.
  Reduced motion removes transition and animation duration.
- Button, input, badge, modal, dropdown, tabs, switch, progress, and empty state
  components expose stable names, state attributes, semantic status text or
  labels, disabled styling, and shared focus treatment.
- App navigation has one owner. `SidebarNavigation` owns desktop route markers,
  so `aria-current="page"` remains unique at the shell level.
- Modal focus enters the dialog, stays contained during Tab navigation, and
  returns to the opener. Dropdown focus enters the first enabled menu item and
  Escape returns focus to the trigger.

## Contrast Measurements

Measured with the WCAG 2 relative-luminance formula against the primary surface:

| Theme | Primary | Secondary | Muted | Accent label on fill |
| --- | ---: | ---: | ---: | ---: |
| Dark | 14.49:1 | 11.06:1 | 8.53:1 | 5.09:1 |
| Light | 14.68:1 | 10.02:1 | 7.74:1 | 7.58:1 |

The measured text pairs exceed 4.5:1. Border and control-boundary validation is
performed by axe's `color-contrast` and `target-size` rules in the route matrix.

## Verification Contract

- Unit coverage validates shared component semantics and navigation ownership.
- Playwright axe coverage scans every configured route at 1440px and 390px in
  both light and dark themes.
- The final human-readable result belongs at
  `frontend-react/artifacts/a11y/final-a11y.md`; raw scan data remains in
  `frontend-react/artifacts/a11y/a11y-report.json`.
