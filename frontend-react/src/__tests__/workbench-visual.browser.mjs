import assert from 'node:assert/strict';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true, ...(process.env.RESPONSIVE_CHROMIUM_PATH ? { executablePath: process.env.RESPONSIVE_CHROMIUM_PATH } : {}) });
try {
  for (const theme of ['dark', 'light']) {
    for (const width of [1280, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 844 } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.addInitScript(() => {
        localStorage.setItem('climber.privacy.skipped', '1');
        localStorage.setItem('i18next_lng', 'en');
      });
      await page.route('**/api/**', route => {
        const path = new URL(route.request().url()).pathname;
        const body = path.endsWith('/messages') ? { messages: [
          { id: 'u', role: 'user', content: 'Review the workspace changes.', tool_calls: [], created_at: '2026-10-02T09:00:00Z' },
          { id: 't', role: 'tool', tool_name: 'read_file', content: 'Layout constraints verified.', tool_calls: [], created_at: '2026-10-02T09:00:01Z' },
          { id: 'a', role: 'assistant', content: '### Workspace review\nThe panels preserve the anchored geometry.\n\n- Inline tool evidence\n- File change markers', tool_calls: [], created_at: '2026-10-02T09:00:02Z' },
        ] } : path.endsWith('/skills') ? [{ id: 'review', name: 'Code review', enabled: true }]
          : path.endsWith('/auth/me') ? { name: 'Reviewer' }
            : path.endsWith('/chat-commands') ? { commands: [] }
              : path.endsWith('/sessions') ? (route.request().method() === 'POST' ? { id: 'visual', title: 'Visual review' } : [{ id: 'visual', title: 'Visual review', status: 'idle' }])
                : path.endsWith('/tasks') || path.endsWith('/traces') || path.includes('/records') ? [] : {};
        return route.fulfill({ contentType: 'application/json', body: JSON.stringify(body) });
      });
      await page.goto('http://localhost:5173/#chat');
      await page.getByTestId('anchored-thinking-bubble').waitFor();
      await page.locator('.boot-splash').waitFor({ state: 'hidden' });
      await page.evaluate(async theme => {
        document.documentElement.dataset.theme = theme;
        const { useAnchoredStore } = await import('/src/store/anchored.ts');
        useAnchoredStore.getState().openFilePreview({ name: 'workspace.ts', path: 'src/workspace.ts', lines: [
          { marker: 'ctx', text: 'export const panels = {' },
          { marker: 'del', text: '  appearance: "flat",' },
          { marker: 'add', text: '  appearance: "anchored",' },
          { marker: 'change', text: '  preserveGeometry: true,' },
          { marker: 'ctx', text: '};' },
        ] });
      }, theme);
      const geometry = await page.evaluate(() => {
        const rect = id => {
          const node = document.querySelector(`[data-testid="${id}"]`);
          if (!node) return null;
          const box = node.getBoundingClientRect();
          return { width: Math.round(box.width), height: Math.round(box.height) };
        };
        return { width: innerWidth, overflow: document.documentElement.scrollWidth > innerWidth, left: rect('anchored-left-nav'), chat: rect('anchored-chat-column'), right: rect('anchored-info-panel'), title: rect('anchored-title-bar'), icons: document.querySelectorAll('[data-workbench-icon]').length };
      });
      assert.equal(geometry.overflow, false);
      assert.equal(geometry.title.height, 48);
      if (width === 1280) {
        assert.equal(geometry.left.width, 240);
        assert.equal(geometry.right.width, 320);
        assert.ok(geometry.chat.width >= 600);
        assert.ok(geometry.icons >= 10);
        await page.getByRole('tab', { name: 'workspace.ts' }).waitFor();
      } else assert.equal(geometry.chat.width, 390);
      await page.screenshot({ path: `/tmp/opencode/workbench-${theme}-${width}.png`, fullPage: true });
      if (width === 390) {
        await page.getByRole('button', { name: 'Expand navigation' }).click();
        assert.ok(await page.getByRole('dialog').locator('[data-workbench-icon="settings"]').count());
        await page.keyboard.press('Escape');
        await page.getByRole('button', { name: 'Info panel', exact: true }).click();
        await page.getByRole('tab', { name: 'workspace.ts' }).waitFor();
        assert.ok(await page.getByRole('dialog').locator('[data-line-marker="change"]').count());
        await page.screenshot({ path: `/tmp/opencode/workbench-${theme}-390-preview.png`, fullPage: true });
      }
      assert.deepEqual(errors, []);
      console.log(JSON.stringify({ theme, ...geometry }));
      await page.close();
    }
  }
} finally { await browser.close(); }
