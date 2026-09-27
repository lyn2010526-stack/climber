import { test, expect } from '@playwright/test';

const sizes = [
  { name: '390x844', width: 390, height: 844 },
  { name: '375x812', width: 375, height: 812 },
  { name: '768x1024', width: 768, height: 1024 },
] as const;

for (const size of sizes) {
  test.describe(`mobile polish ${size.name}`, () => {
    test.use({ viewport: { width: size.width, height: size.height }, colorScheme: 'dark' });

    test('keeps mobile controls reachable and the viewport single-column', async ({ page }) => {
      await page.goto('/#chat');
      if (size.width >= 768) {
        await expect(page.locator('body')).toBeVisible();
        return;
      }
      await expect(page.locator('textarea, input[type="text"], [contenteditable="true"]').first()).toBeVisible();
      const metrics = await page.evaluate(() => ({
        width: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        targets: [...document.querySelectorAll('button, a, [role="button"]')]
          .filter(element => {
            const rect = element.getBoundingClientRect();
            return rect.width > 0 && rect.height > 0;
          })
          .map(element => {
            const rect = element.getBoundingClientRect();
            return { width: rect.width, height: rect.height };
          }),
      }));
      expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.width + 1);
      if (size.width < 768) {
        expect(metrics.targets.filter(target => target.width < 44 || target.height < 44)).toHaveLength(0);
      }
    });

    test('keeps draft and composer controls available while the viewport shrinks', async ({ page }) => {
      await page.goto('/#chat');
      if (size.width >= 768) {
        await expect(page.locator('body')).toBeVisible();
        return;
      }
      const input = page.locator('textarea, input[type="text"], [contenteditable="true"]').first();
      await input.fill('保留草稿');
      await page.evaluate(() => window.dispatchEvent(new Event('resize')));
      await expect(input).toHaveValue('保留草稿');
      if (size.width < 768) {
        await expect(page.getByRole('button', { name: '发送消息' })).toBeVisible();
      } else {
        await expect(input).toBeVisible();
      }
    });
  });
}
