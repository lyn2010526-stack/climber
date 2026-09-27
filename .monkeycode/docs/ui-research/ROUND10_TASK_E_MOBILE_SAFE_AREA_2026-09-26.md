# Task E Mobile Shell Evidence

Date: 2026-09-26. Ownership: E only.

## Changes

- `AdaptiveMobileLayout.tsx` now supplies a status fallback when the page child is absent, preserving a usable mobile shell for an unmapped or failed page.
- `index.css` reserves the bottom navigation height plus a minimum 12px content clearance and applies `env(safe-area-inset-bottom)` to the fixed navigation itself.
- Existing top, left, and right safe-area utilities remain in use by the mobile context bar and mobile chat composer.

## Evidence

- Playwright DOM probe at 390px reported `.mobile-workspace-shell` and `.mobile-bottom-nav` mounted with `scrollWidth === clientWidth` in both themes.
- Existing `AdaptiveMobileLayout.test.tsx` covers the More sheet, adapted entries, and navigation.

## Decision

The safe-area and fallback changes are applied. Device-emulation inset rendering remains pending because the current browser probe does not expose a physical cutout.
