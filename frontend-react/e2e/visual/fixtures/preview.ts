/**
 * Stable serving harness for the pixel layer.
 *
 * The dev server hot-reloads on every source edit, and a reload mid-test leaves
 * a lazy route showing `Loading` with its data fetch never issued — the page
 * photographs blank and the baseline becomes worthless. A production bundle
 * behind `preview` has no HMR socket and no on-demand transform, so the same
 * combination renders the same way every run.
 *
 * Enabled with `VISUAL_PREVIEW=1`; the dev server stays the default so nothing
 * about the existing setup changes.
 */

import type { Page } from '@playwright/test';

export const PREVIEW_PORT = Number(process.env.VISUAL_PREVIEW_PORT || 4319);
export const PREVIEW_ORIGIN = `http://127.0.0.1:${PREVIEW_PORT}`;
export const PREVIEW_DIST = 'dist-visual';

export function previewEnabled(): boolean {
  return process.env.VISUAL_PREVIEW === '1';
}

/**
 * The `webServer` entry Playwright starts before the first test when the
 * preview flag is set. It reuses an already-listening port so re-runs are cheap.
 */
/**
 * Neutralise the dev server's hot-reload channel for a page under test.
 *
 * Vite's client opens a WebSocket and, on a full-reload message, re-evaluates
 * the document. During a run where the source tree is being edited, that lands
 * mid-test: the lazy route remounts, its data fetch is never issued, and the
 * page photographs as `Loading` with no content. The reload is what makes a
 * result untrustworthy, so the channel is closed from the test side rather than
 * by asking the dev server to behave.
 *
 * Only the Vite HMR socket is stubbed; nothing else in the page is affected.
 */
export async function freezeHmr(page: Page): Promise<void> {
  if (!process.env.VISUAL_FREEZE_HMR) return;
  await page.addInitScript(() => {
    const NativeWebSocket = window.WebSocket;
    class FrozenSocket {
      static readonly CONNECTING = 0;
      static readonly OPEN = 1;
      static readonly CLOSING = 2;
      static readonly CLOSED = 3;
      readonly readyState = 3;
      readonly url: string;
      onopen: unknown = null;
      onclose: unknown = null;
      onerror: unknown = null;
      onmessage: unknown = null;
      binaryType = 'blob' as BinaryType;
      bufferedAmount = 0;
      extensions = '';
      protocol = '';
      constructor(url: string | URL) {
        this.url = String(url);
        // Report a closed socket so the Vite client gives up quietly instead of
        // falling back to its polling reconnect loop.
        queueMicrotask(() => {
          const handler = this.onclose as ((event: unknown) => void) | null;
          handler?.({ type: 'close', code: 1000, reason: 'frozen for visual test' });
        });
      }
      send(): void {}
      close(): void {}
      addEventListener(): void {}
      removeEventListener(): void {}
      dispatchEvent(): boolean {
        return true;
      }
    }
    // The stub is intentionally shape-compatible rather than a complete
    // WebSocket; the Vite client only needs open/close/send to give up.
    window.WebSocket = FrozenSocket as unknown as typeof window.WebSocket;
  });
}

export function previewWebServer(): Array<{ command: string; url: string; reuseExistingServer: boolean; timeout: number }> {
  if (!previewEnabled()) return [];
  return [
    {
      command: `npx vite preview --port ${PREVIEW_PORT} --strictPort --host 127.0.0.1 --outDir ${PREVIEW_DIST}`,
      url: PREVIEW_ORIGIN,
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ];
}
