# Resource Pages Polish

Date: 2026-09-26

## Scope

The resource workbench covers agents, skills, MCP servers, and plugins. The UI keeps the same row order across catalogs: identity, description, reported status, source or version, and actions. Loading, empty, filtered-empty, error, retry, and pending-action states remain visible in the same page context.

## Reference Evidence

### Radix Dropdown Menu

Source: https://www.radix-ui.com/primitives/docs/components/dropdown-menu

The official reference defines a dropdown trigger as a button with `aria-haspopup="menu"`, `aria-expanded`, and `aria-controls`. Menu actions are represented by menu items, with keyboard navigation and focus management owned by the menu primitive. This supports keeping row action triggers as real buttons, giving action items explicit menu semantics, and avoiding nested interactive wrappers.

### VS Code Extensions View

Source: https://code.visualstudio.com/docs/editor/extension-marketplace

The Extensions view presents installed extensions with publisher and version metadata, then exposes install, enable, disable, and uninstall actions according to the extension lifecycle. The resource pages apply the same operational hierarchy: source and version are metadata, while status and available actions are separate fields.

### GitHub Primer Search Patterns

Source: https://primer.style/product/components/action-list

Primer's action-list guidance treats filtering and actions as distinct controls and keeps labels available to assistive technology. The resource rows follow this pattern with shared `includesQuery`, explicit filter groups, labeled status text, and text-plus-icon actions.

## Decisions Applied

- Backend status values are normalized through a shared vocabulary. Missing or unknown values render `Unreported` and do not imply installed or enabled.
- Pending actions disable the complete row action set and retain the returned error beside the affected row.
- Catalog rows use wrapping flex layouts at narrow widths. Icon-only controls have a minimum 44px touch target.
- Badge is an inline `span`, which keeps badges valid inside headings, labels, and other phrasing-content containers.
- Marketing claims, decorative glyphs, and unverified `official` or `featured` labels are excluded from resource rows.
