import { useState } from 'react';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GlobalSearch } from '../GlobalSearch';
import { api } from '../../../api';

const { t } = vi.hoisted(() => ({ t: (key: string) => key }));
vi.mock('../../../i18n', () => ({ useI18n: () => ({ t }) }));
vi.mock('../../../api', () => ({ api: { search: vi.fn() } }));

const rows = [
  { id: 'same', type: 'document', title: 'Document result', preview: 'Document preview', score: 1, timestamp: '' },
  { id: 'same', type: 'memory', title: 'Memory result', preview: 'Memory preview', score: 1, timestamp: '' },
];
const search = vi.mocked(api.search);
async function debounce() { await act(async () => { await vi.advanceTimersByTimeAsync(300); }); }
function query(value: string) { fireEvent.change(screen.getByRole('combobox'), { target: { value } }); }

beforeEach(() => { vi.useFakeTimers(); search.mockReset(); search.mockResolvedValue(rows); });
afterEach(() => { cleanup(); vi.useRealTimers(); });

describe('GlobalSearch', () => {
  it('debounces trimmed searches, selects results, and expands previews with Enter or click', async () => {
    render(<GlobalSearch isOpen onClose={vi.fn()} />);
    expect(screen.getByRole('combobox')).toHaveFocus();
    query('a');
    await debounce();
    expect(search).not.toHaveBeenCalled();
    query('  document  ');
    expect(screen.getByRole('status')).toHaveTextContent('global_search.searching');
    await debounce();
    expect(search).toHaveBeenCalledWith('document', 20);
    const input = screen.getByRole('combobox');
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    const options = screen.getAllByRole('option');
    expect(options[1]).toHaveAttribute('aria-selected', 'true');
    expect(input).toHaveAttribute('aria-activedescendant', options[1].id);
    fireEvent.keyDown(input, { key: 'Enter', isComposing: true });
    expect(screen.getByText('Memory preview')).toHaveClass('truncate');
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(screen.getByText('Memory preview')).toHaveClass('whitespace-pre-wrap');
    // A preview-only row names the preview span and the reason it cannot open.
    expect(options[1]!.getAttribute('aria-describedby')!.split(' ')).toEqual([
      screen.getByText('Memory preview').id,
      screen.getByText('global_search.preview_only.memory').id,
    ]);
    fireEvent.click(options[1]!);
    expect(screen.getByText('Memory preview')).toHaveClass('truncate');
    expect(screen.getByRole('option', { selected: true })).toHaveAttribute('aria-describedby');
    expect(screen.getByRole('group', { name: 'common.filter' })).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toHaveAccessibleName('sidebar.global_search');
    fireEvent.click(screen.getByRole('button', { name: 'global_search.document' }));
    expect(screen.getByRole('option')).toHaveAttribute('aria-selected', 'true');
    fireEvent.click(screen.getByRole('button', { name: 'global_search.group' }));
    expect(screen.getByRole('status')).toHaveTextContent('common.no_results');
    expect(input).not.toHaveAttribute('aria-activedescendant');
  });

  it('shows recoverable errors and retries the current query', async () => {
    search.mockRejectedValueOnce(new Error('Offline'));
    render(<GlobalSearch isOpen onClose={vi.fn()} />);
    query('document');
    await debounce();
    expect(screen.getByRole('alert')).toHaveTextContent('common.network_error');
    fireEvent.click(screen.getByRole('button', { name: 'common.retry' }));
    await debounce();
    expect(search).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getAllByRole('option')).toHaveLength(2);
  });

  it('ignores older responses while a newer request is still loading', async () => {
    let resolveOld!: (value: typeof rows) => void;
    let resolveNew!: (value: typeof rows) => void;
    search.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }));
    search.mockImplementationOnce(() => new Promise(resolve => { resolveNew = resolve; }));
    render(<GlobalSearch isOpen onClose={vi.fn()} />);
    query('old');
    await debounce();
    query('new');
    await debounce();
    await act(async () => resolveOld(rows));
    expect(screen.getByRole('status')).toHaveTextContent('global_search.searching');
    expect(screen.queryByRole('option')).not.toBeInTheDocument();
    await act(async () => resolveNew([rows[1]]));
    expect(screen.getByRole('option')).toHaveTextContent('Memory result');
  });

  it('reports malformed results without crashing the dialog', async () => {
    search.mockResolvedValueOnce([null]);
    render(<GlobalSearch isOpen onClose={vi.fn()} />);
    query('invalid');
    await debounce();
    expect(screen.getByRole('alert')).toHaveTextContent('common.network_error');
    expect(screen.getByRole('combobox')).toHaveFocus();
  });

  it('ignores stale failures after clearing, closing and reopening', async () => {
    let rejectOld!: (error: Error) => void;
    search.mockImplementationOnce(() => new Promise((_resolve, reject) => { rejectOld = reject; }));
    const { rerender } = render(<GlobalSearch isOpen onClose={vi.fn()} />);
    query('old');
    await debounce();
    query('');
    expect(screen.getByRole('status')).toHaveTextContent('global_search.placeholder');
    rerender(<GlobalSearch isOpen={false} onClose={vi.fn()} />);
    rerender(<GlobalSearch isOpen onClose={vi.fn()} />);
    await act(async () => rejectOld(new Error('Stale failure')));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('combobox')).toHaveValue('');
    expect(screen.queryByRole('option')).not.toBeInTheDocument();
  });

  it('cancels pending debounce work on close and makes no requests while hidden', async () => {
    const { rerender } = render(<GlobalSearch isOpen onClose={vi.fn()} />);
    query('pending');
    rerender(<GlobalSearch isOpen={false} onClose={vi.fn()} />);
    await debounce();
    expect(search).not.toHaveBeenCalled();
  });

  it('keeps focus within the dialog and restores its opener on Escape', async () => {
    vi.useRealTimers();
    const user = userEvent.setup();
    function Harness() {
      const [open, setOpen] = useState(false);
      return <><button onClick={() => setOpen(true)}>Launch</button><GlobalSearch isOpen={open} onClose={() => setOpen(false)} /></>;
    }
    render(<Harness />);
    await user.click(screen.getByText('Launch'));
    await user.tab({ shift: true });
    expect(screen.getByRole('button', { name: 'global_search.group' })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole('combobox')).toHaveFocus();
    await user.keyboard('{Escape}');
    await waitFor(() => expect(screen.getByText('Launch')).toHaveFocus());
  });

  it('keeps one close affordance instead of two escape labels', () => {
    render(<GlobalSearch isOpen onClose={vi.fn()} />);
    expect(screen.queryByText(/^esc$/i)).not.toBeInTheDocument();
    expect(screen.getByText('common.navigate')).toBeInTheDocument();
    expect(screen.getByText('common.open')).toBeInTheDocument();
    expect(screen.queryByText('common.close')).not.toBeInTheDocument();
  });

  it('jumps to both ends of the result list', async () => {
    render(<GlobalSearch isOpen onClose={vi.fn()} />);
    query('document');
    await debounce();
    const input = screen.getByRole('combobox');
    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(input, { key: 'End' });
    expect(options[options.length - 1]).toHaveAttribute('aria-selected', 'true');
    expect(input).toHaveAttribute('aria-activedescendant', options[options.length - 1].id);
    fireEvent.keyDown(input, { key: 'Home' });
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
    expect(input).toHaveAttribute('aria-activedescendant', options[0].id);
  });

  it('marks the selected row in the list and keeps icons out of the name', async () => {
    render(<GlobalSearch isOpen onClose={vi.fn()} />);
    query('document');
    await debounce();
    const options = screen.getAllByRole('option');
    expect(options[0]).toHaveTextContent('Document result');
    expect(options[0]).not.toHaveTextContent('FileText');
    fireEvent.mouseEnter(options[1]!);
    expect(options[1]).toHaveAttribute('aria-selected', 'true');
  });

  describe('navigation', () => {
    const groupRow = { id: 'g1', type: 'group', title: 'Group result', preview: 'Group preview', score: 1, timestamp: '' };
    const documentRow = { id: 'd1', type: 'document', title: 'Document result', preview: 'Document preview', score: 1, timestamp: '' };
    const memoryRow = { id: 'm1', type: 'memory', title: 'Memory result', preview: 'Memory preview', score: 1, timestamp: '' };

    it('opens a group on its page with Enter and closes the dialog', async () => {
      const onNavigate = vi.fn();
      const onClose = vi.fn();
      search.mockResolvedValue([groupRow]);
      render(<GlobalSearch isOpen onClose={onClose} onNavigate={onNavigate} />);
      query('group');
      await debounce();
      const input = screen.getByRole('combobox');
      fireEvent.keyDown(input, { key: 'Enter' });
      expect(onNavigate).toHaveBeenCalledWith({ page: 'cluster', result: groupRow });
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it('opens a group on click as well as on Enter', async () => {
      const onNavigate = vi.fn();
      search.mockResolvedValue([groupRow]);
      render(<GlobalSearch isOpen onClose={vi.fn()} onNavigate={onNavigate} />);
      query('group');
      await debounce();
      fireEvent.click(screen.getByRole('option'));
      expect(onNavigate).toHaveBeenCalledWith({ page: 'cluster', result: groupRow });
    });

    it('keeps a document chunk and a memory in the dialog, and says why', async () => {
      const onNavigate = vi.fn();
      const onClose = vi.fn();
      search.mockResolvedValue([documentRow, memoryRow]);
      render(<GlobalSearch isOpen onClose={onClose} onNavigate={onNavigate} />);
      query('result');
      await debounce();
      const input = screen.getByRole('combobox');
      expect(screen.getByText('global_search.preview_only.document')).toBeInTheDocument();
      expect(screen.getByText('global_search.preview_only.memory')).toBeInTheDocument();
      // No group row, so nothing in this list may route anywhere.
      expect(screen.queryByText('global_search.preview_only.group')).not.toBeInTheDocument();

      fireEvent.keyDown(input, { key: 'Enter' });
      expect(onNavigate).not.toHaveBeenCalled();
      expect(onClose).not.toHaveBeenCalled();
      // Enter still does its one useful thing: reveal the whole preview.
      expect(screen.getByText('Document preview')).toHaveClass('whitespace-pre-wrap');

      fireEvent.keyDown(input, { key: 'ArrowDown' });
      fireEvent.keyDown(input, { key: 'Enter' });
      expect(onNavigate).not.toHaveBeenCalled();
      expect(screen.getByText('Memory preview')).toHaveClass('whitespace-pre-wrap');
    });

    it('leaves Enter inert on a preview-only row when it has no text to reveal', async () => {
      const onNavigate = vi.fn();
      search.mockResolvedValue([{ ...memoryRow, preview: '' }]);
      render(<GlobalSearch isOpen onClose={vi.fn()} onNavigate={onNavigate} />);
      query('memory');
      await debounce();
      fireEvent.keyDown(screen.getByRole('combobox'), { key: 'Enter' });
      expect(onNavigate).not.toHaveBeenCalled();
      expect(screen.getByRole('option')).toHaveTextContent('global_search.preview_only.memory');
    });

    it('never routes when the caller supplies no navigation handler', async () => {
      search.mockResolvedValue([groupRow]);
      render(<GlobalSearch isOpen onClose={vi.fn()} />);
      query('group');
      await debounce();
      // Without a handler there is nowhere to go, so the row says preview-only
      // and Enter reveals the text instead of leaving the dialog.
      expect(screen.getByText('global_search.preview_only.group')).toBeInTheDocument();
      fireEvent.keyDown(screen.getByRole('combobox'), { key: 'Enter' });
      expect(screen.getByRole('option')).toHaveTextContent('Group preview');
    });

    it('keeps Enter on the row the keyboard walked to', async () => {
      const onNavigate = vi.fn();
      search.mockResolvedValue([groupRow, documentRow]);
      render(<GlobalSearch isOpen onClose={vi.fn()} onNavigate={onNavigate} />);
      query('result');
      await debounce();
      const input = screen.getByRole('combobox');
      fireEvent.keyDown(input, { key: 'ArrowDown' });
      fireEvent.keyDown(input, { key: 'Enter' });
      // The second row is a document chunk, so the group row is never opened.
      expect(onNavigate).not.toHaveBeenCalled();
    });
  });

  describe('document chunk responses', () => {
    it('reads the backend chunk shape into a document row', async () => {
      // `GET /search` answers with { id, document_id, content, chunk_index,
      // score, created_at } and no type/title/preview.
      search.mockResolvedValue([
        { id: 'chunk-1', document_id: 'doc-9', content: 'the matched sentence', chunk_index: 2, score: 0, created_at: '2026-01-01T00:00:00' },
      ]);
      render(<GlobalSearch isOpen onClose={vi.fn()} onNavigate={vi.fn()} />);
      query('sentence');
      await debounce();
      const option = screen.getByRole('option');
      expect(option).toHaveTextContent('doc-9');
      expect(option).toHaveTextContent('the matched sentence');
      expect(option).toHaveTextContent('global_search.document');
      // A chunk has no detail page, so it stays a preview.
      expect(option).toHaveTextContent('global_search.preview_only.document');
    });

    it('rejects a row with no usable identity', async () => {
      search.mockResolvedValue([{ content: 'orphan text' }]);
      render(<GlobalSearch isOpen onClose={vi.fn()} />);
      query('orphan');
      await debounce();
      expect(screen.getByRole('alert')).toHaveTextContent('common.network_error');
    });
  });
});
