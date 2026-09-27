# Mobile Responsive Adaptation Research

## Scope

This note records the mobile-only implementation decisions for 375px, 390px, and 768px layouts. Desktop workspace layout and locale aggregate files remain outside the change surface.

## Reference Findings

- `assistant-ui` treats the composer as an in-flow primitive with a send/cancel state pair. Its mobile pattern keeps the input at a 16px minimum, uses thumb-sized controls, and changes auxiliary content when the keyboard is visible.
- `open-webui` compares `visualViewport.height` with `window.innerHeight`, listens to both `resize` and `scroll`, and coalesces updates through `requestAnimationFrame`. Its Safari IME guard consumes one Enter close to `compositionend`.
- `lobe-chat` keeps mobile routes isolated from desktop composition and uses drawer surfaces as explicit stateful navigation boundaries.

## Local Contracts

- The mobile shell owns viewport clamping. The chat page only fills the shell content box, which keeps the draft and composer mounted through keyboard resize events.
- The bottom navigation reserve is a single CSS variable containing the navigation strip plus a minimum safe-area gap. The composer adds the device bottom inset once through `max(12px, env(safe-area-inset-bottom))`.
- The More navigation is an ARIA modal dialog with a close button, focus entry, Tab wrapping, Escape dismissal, outside-pointer dismissal, and trigger focus restoration.
- IME confirmation is ignored while composition is active, for `keyCode === 229`, and for the single Safari confirmation Enter within 500ms of `compositionend`.

## Verification Matrix

- 375px: five navigation targets remain in equal grid columns; composer controls retain 44px targets and 16px text.
- 390px: message content wraps inside the shell and the composer remains in flow above the navigation reserve.
- 768px: mobile shell is hidden at the desktop breakpoint, preserving desktop layout ownership.
