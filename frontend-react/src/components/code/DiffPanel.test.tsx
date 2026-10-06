import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import i18n from '../../i18n/config';
import { DiffPanel, parseDiff } from './DiffPanel';

const DIFF = `diff --git a/src/app.ts b/src/app.ts
index 1111111..2222222 100644
--- a/src/app.ts
+++ b/src/app.ts
@@ -1,4 +1,5 @@
 const label = "before";
-const removed = 1;
+const added = 2;
+// a comment
 const tail = true;
`;

describe('DiffPanel', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('zh-CN');
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } });
  });

  it('parses a unified diff into files, hunks and rows', () => {
    const [file] = parseDiff(DIFF);
    expect(file.path).toBe('src/app.ts');
    expect(file.hunks).toHaveLength(1);
    expect(file.hunks[0].header).toContain('@@');
    expect(file.hunks[0].rows.map((row) => row.kind)).toEqual([
      'ctx', 'del', 'add', 'add', 'ctx',
    ]);
    expect(file.additions).toBe(2);
    expect(file.deletions).toBe(1);
  });

  it('gives each row the diff role class index.css publishes for it', () => {
    const { container } = render(<DiffPanel diffText={DIFF} />);
    expect(container.querySelectorAll('.diff-hunk-header')).toHaveLength(1);
    expect(container.querySelectorAll('.diff-line-added')).toHaveLength(2);
    expect(container.querySelectorAll('.diff-line-removed')).toHaveLength(1);
    expect(container.querySelector('.diff-hunk-header')?.textContent).toContain('@@');
  });

  it('takes the added/removed counts from the diff tokens, not success/error', () => {
    const { container } = render(<DiffPanel diffText={DIFF} />);
    const counts = Array.from(container.querySelectorAll('span'))
      .map((node) => node.textContent ?? '')
      .filter((text) => /^[+-]\d+$/.test(text.trim()));
    expect(counts.map((text) => text.trim())).toEqual(expect.arrayContaining(['+2', '-1']));
    // The semantic success/error colours are body-text roles; a diff line is
    // not body text, so neither may appear anywhere in the panel.
    expect(container.innerHTML).not.toContain('--color-success');
    expect(container.innerHTML).not.toContain('--color-error');
  });

  it('highlights keywords, strings, numbers and comments with syntax tokens', () => {
    const { container } = render(<DiffPanel diffText={DIFF} />);
    const html = container.innerHTML;
    expect(html).toContain('--color-syntax-keyword');
    expect(html).toContain('--color-syntax-string');
    expect(html).toContain('--color-syntax-number');
    expect(html).toContain('--color-syntax-comment');
  });

  it('shows the line-number gutter only when asked', () => {
    const withNumbers = render(<DiffPanel diffText={DIFF} />);
    // Two numbers per row: the old and the new line, both tabular.
    const added = withNumbers.container.querySelector('.diff-line-added');
    expect(within(added as HTMLElement).getAllByText(/^\d+$/)).toHaveLength(2);
    withNumbers.unmount();

    // The header keeps its own tabular counts; only the per-line gutter goes.
    const { container } = render(<DiffPanel diffText={DIFF} showLineNumbers={false} />);
    expect(container.querySelector('.diff-line-added')?.querySelectorAll('.tabular-nums')).toHaveLength(0);
    expect(container.querySelector('.diff-line-added')?.textContent?.trim().startsWith('+')).toBe(true);
  });

  it('confirms a copy with the success tone', async () => {
    const { container } = render(<DiffPanel diffText={DIFF} />);
    await userEvent.click(screen.getByRole('button', { name: /复制/ }));

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining('const added = 2;'));
    expect(screen.getByRole('button', { name: '已复制' })).toBeTruthy();
    expect(container.querySelector('.text-\\[var\\(--color-success\\)\\]')).toBeTruthy();
  });

  it('reports a copy failure through the error tone instead of a fixed colour', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) },
    });
    const { container } = render(<DiffPanel diffText={DIFF} />);
    await userEvent.click(screen.getByRole('button', { name: /复制/ }));

    // The failure is an alert, not a silent no-op, and it is a status error.
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain('复制失败');
    expect(alert.querySelector('.text-\\[var\\(--color-error\\)\\]')).toBeTruthy();
    expect(container.querySelector('.text-\\[var\\(--color-error\\)\\]')).toBeTruthy();
  });

  it('states that there is nothing to show when there is no diff', () => {
    render(<DiffPanel />);
    const status = screen.getByRole('status');
    expect(status.textContent).toContain('暂无文件变更');
  });

  it('keeps a line of added code readable as text, glyphs aside', () => {
    const { container } = render(<DiffPanel diffText={DIFF} />);
    const added = container.querySelector('.diff-line-added');
    expect(added).toBeTruthy();
    // Token spans split the source, so read the whole line and drop the
    // gutter before comparing.
    const text = (added?.textContent ?? '').replace(/^\s*\d*\s*\d*\s*\+/, '').trim();
    expect(text).toBe('const added = 2;');
    expect(within(added as HTMLElement).queryByText('const')).toBeTruthy();
  });
});
