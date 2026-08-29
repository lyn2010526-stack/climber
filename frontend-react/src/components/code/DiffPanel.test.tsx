import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DiffPanel } from './DiffPanel';

const diffText = `diff --git a/src/example.ts b/src/example.ts
--- a/src/example.ts
+++ b/src/example.ts
@@ -1 +1 @@
-const value = 1;
+const value = 2;`;

describe('DiffPanel', () => {
  it('exposes separate expand and copy controls', async () => {
    const user = userEvent.setup();
    const writeText = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue(undefined);
    render(<DiffPanel diffText={diffText} />);

    const expandButton = screen.getByRole('button', { name: '收起 src/example.ts' });
    const copyButton = screen.getByRole('button', { name: '复制 src/example.ts 的差异' });
    const contentId = expandButton.getAttribute('aria-controls');

    expect(expandButton).toHaveAttribute('aria-expanded', 'true');
    expect(document.getElementById(contentId ?? '')).toBeInTheDocument();
    expect(expandButton.contains(copyButton)).toBe(false);

    await user.click(expandButton);
    expect(expandButton).toHaveAttribute('aria-expanded', 'false');
    expect(document.getElementById(contentId ?? '')).not.toBeInTheDocument();

    await user.click(copyButton);
    expect(writeText).toHaveBeenCalledOnce();
  });
});
