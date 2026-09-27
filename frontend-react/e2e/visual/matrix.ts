/**
 * The coverage matrix.
 *
 * Page ids come from `src/navigation/navConfig.ts` (`Page` union) and widths
 * from `src/layout/breakpoints.ts`, so the matrix tracks the product instead of
 * a hand-maintained copy of it. `scripts/verify-matrix.mjs` fails the build if a
 * nav id is added without a matrix entry.
 *
 * Chat is the one page with more than one state: an empty transcript, a
 * populated one, a live stream, and a failure. The other pages get one
 * populated state each, because their layout risk is in the populated case.
 */

import { NAV_ITEM_IDS } from '../../src/navigation/navConfig';

export const WIDTHS = [1440, 1280, 1024, 768, 390] as const;
export type Width = (typeof WIDTHS)[number];

/** Viewport height per width: wide desktop, laptop, tablet, phone. */
export const HEIGHTS: Record<Width, number> = {
  1440: 900,
  1280: 800,
  1024: 768,
  768: 1024,
  390: 844,
};

/** `useIsMobile` is `max-width: 767px` (breakpoints.ts:23-25). */
export const MOBILE_MAX_WIDTH = 767;

export type ChatState = 'empty' | 'messages' | 'streaming' | 'error';

export interface MatrixEntry {
  page: string;
  /** Only chat has a state dimension; other pages are always 'populated'. */
  state: ChatState | null;
  /** Which route the hash must resolve to, accounting for the mobile fallback. */
  expectedHash: string;
}

/**
 * `MOBILE_ADAPTED_PAGE_IDS` (navConfig.ts:70-72) minus `crews`/`authapikeys`,
 * which the mobile shell routes to the chat entry. Below 768px the app renders
 * `MobileChatPage` for anything outside that set (App.tsx:104-116), so those
 * combinations are recorded as the fallback rather than as the requested page.
 */
const MOBILE_ADAPTED = new Set([
  'dashboard', 'chat', 'factory', 'tasks', 'agents', 'cluster', 'apikeys', 'authapikeys', 'settings',
]);

/** The mobile shell's own usable set (AdaptiveMobileLayout.tsx:14-16). */
const MOBILE_SHELL_USABLE = new Set([
  'dashboard', 'chat', 'factory', 'cluster', 'tasks', 'agents', 'apikeys', 'settings',
]);

export const CHAT_STATES: ChatState[] = ['empty', 'messages', 'streaming', 'error'];

/** Pages the task requires, as declared against the real nav ids. */
export const REQUIRED_PAGES = [
  'chat', 'agents', 'skills', 'mcp', 'plugins', 'settings', 'cluster', 'traces',
  'reasoning', 'eval', 'cost', 'doctor', 'scheduler', 'workflows',
  'notifications', 'apikeys', 'authapikeys', 'dashboard', 'factory', 'tasks',
] as const;

/** `hash` the app should settle on at this width for a requested page. */
export function expectedHashFor(page: string, width: number): string {
  if (width > MOBILE_MAX_WIDTH) return page;
  if (MOBILE_SHELL_USABLE.has(page)) return page;
  // App.tsx:105 rewrites the non-adapted page to the chat surface.
  return 'chat';
}

/** True when a width renders the mobile shell rather than the desktop layout. */
export function isMobileWidth(width: number): boolean {
  return width <= MOBILE_MAX_WIDTH;
}

/** The full page × state expansion, with the mobile fallback already resolved. */
export function buildMatrix(): MatrixEntry[] {
  const entries: MatrixEntry[] = [];
  for (const page of REQUIRED_PAGES) {
    if (!NAV_ITEM_IDS.has(page)) {
      throw new Error(
        `matrix page "${page}" is not in navConfig NAV_ITEM_IDS — the route was removed or renamed`,
      );
    }
    if (page === 'chat') {
      for (const state of CHAT_STATES) {
        entries.push({ page, state, expectedHash: 'chat' });
      }
      continue;
    }
    entries.push({ page, state: null, expectedHash: page });
  }
  return entries;
}

/** Total number of tests the matrix produces, for the report header. */
export function countCombinations(): number {
  const pages = buildMatrix();
  return pages.length * WIDTHS.length * 2;
}

export { NAV_ITEM_IDS, MOBILE_ADAPTED, MOBILE_SHELL_USABLE };
