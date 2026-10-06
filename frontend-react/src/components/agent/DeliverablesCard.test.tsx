import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import type { DeliverableEntry } from './deliverables';
import { DeliverablesCard } from './DeliverablesCard';

const files: DeliverableEntry[] = [
  { path: 'src/components/a.ts', added: 4, removed: 1, kind: 'file' },
  { path: 'app/page.tsx', added: 2, removed: 0, kind: 'file' },
];
const website: DeliverableEntry = { path: 'https://example.com/preview', added: 0, removed: 0, kind: 'website' };

beforeEach(async () => {
  await i18n.changeLanguage('zh-CN');
});

describe('DeliverablesCard', () => {
  const openSpy = vi.fn();
  let windowOpen: typeof window.open;

  beforeEach(() => {
    openSpy.mockClear();
    windowOpen = window.open;
    window.open = vi.fn();
  });
  afterEach(() => {
    window.open = windowOpen;
  });

  it('summarizes the number of edited files and shows changes by default', () => {
    render(<DeliverablesCard entries={files} onOpenFile={openSpy} />);
    expect(screen.getByText('编辑了 2 个文件')).toBeVisible();
    expect(screen.getByRole('button', { name: /查看变更/ })).toBeVisible();
    expect(screen.getByText('a.ts')).toBeVisible();
    expect(screen.getByText('page.tsx')).toBeVisible();
    expect(screen.getByText('app/')).toBeVisible();
  });

  it('opens the file preview when a file row is clicked', async () => {
    const user = userEvent.setup();
    render(<DeliverablesCard entries={files} onOpenFile={openSpy} />);
    await user.click(screen.getByText('a.ts'));
    expect(openSpy).toHaveBeenCalledWith('src/components/a.ts');
  });

  it('opens websites in a new tab from the row or the header shortcut', async () => {
    const user = userEvent.setup();
    render(<DeliverablesCard entries={[website]} onOpenFile={openSpy} />);
    expect(screen.getByText('1 个网页')).toBeVisible();
    await user.click(screen.getByText('https://example.com/preview'));
    expect(window.open).toHaveBeenCalledWith('https://example.com/preview', '_blank', 'noopener,noreferrer');
  });

  it('hides extra entries behind a more button and collapses again', async () => {
    const user = userEvent.setup();
    const many = [...files, ...files, { ...website, path: 'https://example.com/x' }];
    render(<DeliverablesCard entries={many} onOpenFile={openSpy} />);
    expect(screen.getByText(/还有 2 项/)).toBeVisible();
    expect(screen.queryByText('https://example.com/x')).toBeNull();
    await user.click(screen.getByRole('button', { name: /还有/ }));
    expect(screen.getByText('https://example.com/x')).toBeVisible();
    await user.click(screen.getByRole('button', { name: /收起/ }));
    expect(screen.queryByText('https://example.com/x')).toBeNull();
  });

  it('marks the summary with items when the turn mixes files and websites', () => {
    render(<DeliverablesCard entries={[...files, website]} onOpenFile={openSpy} />);
    expect(screen.getByText('3 项交付物')).toBeVisible();
  });
});