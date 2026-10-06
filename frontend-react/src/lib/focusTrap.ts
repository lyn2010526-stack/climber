/**
 * Focus containment for dialog surfaces.
 *
 * `aria-modal="true"` promises assistive technology that the rest of the page is
 * inert. That promise only holds if Tab actually stays inside the dialog, so
 * every modal surface resolves its tab stops through this one selector. Keeping
 * a single list means a new dialog type cannot ship with a narrower one.
 */
const FOCUSABLE_SELECTOR = [
  'button:not([disabled])',
  '[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'summary',
  'audio[controls]',
  'video[controls]',
  '[contenteditable]:not([contenteditable="false"])',
  '[tabindex]',
].join(',');

/** Elements that exclude themselves from the tab order. */
const NEGATIVE_TABINDEX = /^-[1-9][0-9]*$/;

/**
 * True when `element` is not hidden by CSS.
 *
 * A `display: none` ancestor hides a whole subtree, so the chain up to the
 * root is checked as well. `visibility: hidden` only hides the element itself
 * unless a descendant opts back in, which is rare inside a dialog, so the
 * element's own value is enough for that case.
 */
function isCssVisible(element: HTMLElement): boolean {
  let node: HTMLElement | null = element;
  while (node) {
    if (window.getComputedStyle(node).display === 'none') return false;
    node = node.parentElement;
  }
  return window.getComputedStyle(element).visibility !== 'hidden';
}

/**
 * Visible, enabled tab stops inside `root`, in document order.
 *
 * Hidden subtrees are skipped because a `display: none` control cannot receive
 * focus, and stepping onto one silently breaks the trap.
 */
export function collectFocusable(root: HTMLElement): HTMLElement[] {
  const candidates = root.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
  const stops: HTMLElement[] = [];
  for (const element of Array.from(candidates)) {
    const tabindex = element.getAttribute('tabindex');
    if (tabindex !== null && NEGATIVE_TABINDEX.test(tabindex)) continue;
    if (element.closest('[inert]')) continue;
    if (element.hidden) continue;
    if (element.getAttribute('aria-hidden') === 'true') continue;
    if (!isCssVisible(element)) continue;
    stops.push(element);
  }
  return stops;
}

/**
 * Moves focus inside `root` for a Tab or Shift+Tab press, wrapping at both ends.
 * Returns true when the press was handled, so the caller can preventDefault.
 */
export function trapTab(root: HTMLElement, shift: boolean): boolean {
  const stops = collectFocusable(root);
  if (stops.length === 0) {
    root.focus();
    return true;
  }
  const first = stops[0]!;
  const last = stops[stops.length - 1]!;
  const active = document.activeElement;

  if (active === root || !root.contains(active)) {
    (shift ? last : first).focus();
    return true;
  }
  if (shift && active === first) {
    last.focus();
    return true;
  }
  if (!shift && active === last) {
    first.focus();
    return true;
  }
  return false;
}
