# Task D Keyboard And Screen Boundary Evidence

Date: 2026-09-26. Ownership: D only. `CommandPalette.tsx` and `GlobalSearch.tsx` were read-only because they are occupied.

## Source Evidence

- `CommandPalette.tsx:93-114` uses a combobox with ArrowUp/ArrowDown bounds, IME protection, Enter activation, and `aria-activedescendant`.
- `CommandPalette.tsx:80` bounds the dialog to `calc(100% - 2rem)` and `84dvh`; its result list uses `min-h-0` and local overflow.
- `GlobalSearch.tsx:127-148` provides equivalent keyboard bounds, IME protection, and result expansion without moving focus away from the input.
- `GlobalSearch.tsx:119` uses the same viewport width and height boundary; Radix focus restoration is wired at lines 110-118.

## Decision

Static keyboard and viewport contracts are present. Real keyboard interaction and focus-return browser runs remain pending because this lane did not modify occupied files.
