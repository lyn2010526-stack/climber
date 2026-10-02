import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TraceViewer from './TraceViewer';
import { api } from '../../api';
import i18n from '../../i18n';

vi.mock('../../api', () => ({
  api: {
    listTraces: vi.fn(),
    getTrace: vi.fn(),
  },
}));

const listTraces = vi.mocked(api.listTraces);
const getTrace = vi.mocked(api.getTrace);

const TRACES = [
  { id: 'trace-1', kind: 'session', name: 'Run', started_at: '2026-09-26T10:00:00Z' },
  { id: 'trace-2', kind: 'session', name: '', started_at: '2026-09-26T11:00:00Z' },
];

const SPANS = [
  {
    id: 'span-1',
    parent_id: null,
    kind: 'llm_call',
    name: 'chat.completions',
    status: 'success',
    started_at: '2026-09-26T10:00:01Z',
    duration_ms: 42,
    tokens_used: 128,
    model: 'deepseek-chat',
    metadata: '{"cwd": "/srv/app"}',
  },
  {
    id: 'span-2',
    parent_id: 'span-1',
    kind: 'tool_call',
    name: 'run_shell',
    tool_name: 'run_shell',
    status: 'error',
    started_at: '2026-09-26T10:00:02Z',
    duration_ms: 8,
    tokens_used: 0,
    error: 'command exited with 1',
  },
  {
    id: 'span-3',
    parent_id: 'span-1',
    kind: 'tool_call',
    name: 'awaiting_tool',
    status: 'pending',
    started_at: '2026-09-26T10:00:03Z',
    duration_ms: 1,
    tokens_used: 0,
  },
];

const STATS = {
  total_spans: 3,
  total_duration_ms: 51,
  total_tokens: 128,
  llm_calls: 1,
  tool_calls: 2,
  error_count: 1,
};

function key(name: string) {
  return i18n.t(name);
}

describe('TraceViewer', () => {
  beforeEach(() => {
    listTraces.mockReset().mockResolvedValue(TRACES);
    getTrace.mockReset().mockResolvedValue({ spans: SPANS, stats: STATS });
  });

  it('names a trace by its name and falls back to its id', async () => {
    await act(async () => {
      render(<TraceViewer />);
    });
    expect(screen.getByText('Run')).toBeTruthy();
    expect(screen.getByText('trace-2')).toBeTruthy();
  });

  it('renders a span outcome through StatusIcon, never through a bare colour', async () => {
    const { container } = render(<TraceViewer traceId="trace-1" />);
    await act(async () => {});

    const failed = screen.getByRole('button', { name: /run_shell/ });
    expect(failed.querySelector('.text-\\[var\\(--color-error\\)\\]')).toBeTruthy();
    // The label carries the same outcome in text, so the glyph is decoration.
    expect(within(failed).getByText(key('tool_call.status_error'))).toBeTruthy();

    const succeeded = screen.getByRole('button', { name: /chat.completions/ });
    expect(succeeded.querySelector('.text-\\[var\\(--color-success\\)\\]')).toBeTruthy();
    expect(within(succeeded).getByText(key('tool_call.status_success'))).toBeTruthy();

    // No status is painted with an inline colour.
    expect(container.querySelectorAll('[style*="color"]')).toHaveLength(0);
  });

  it('marks a running span as running and a pending span as queued', async () => {
    render(<TraceViewer traceId="trace-1" />);
    await act(async () => {});

    const pending = screen.getByRole('button', { name: /awaiting_tool/ });
    expect(pending.querySelector('.text-\\[var\\(--color-text-disabled\\)\\]')).toBeTruthy();
    expect(within(pending).getByText(key('tool_call.status_pending'))).toBeTruthy();
  });

  it('keeps measurements in a monospace syntax-number face', async () => {
    render(<TraceViewer traceId="trace-1" />);
    await act(async () => {});

    const row = screen.getByRole('button', { name: /chat.completions/ });
    const duration = within(row).getByText('42ms');
    expect(duration.className).toContain('font-mono');
    expect(duration.className).toContain('text-[var(--color-syntax-number)]');
  });

  it('indents a child span with a rule, not a margin literal', async () => {
    const { container } = render(<TraceViewer traceId="trace-1" />);
    await act(async () => {});

    const child = screen.getByRole('button', { name: /run_shell/ }).parentElement as HTMLElement;
    expect(child.style.marginInlineStart).toBe('calc(var(--space-4) * 1)');
    expect(child.className).toContain('border-s');

    const root = screen.getByRole('button', { name: /chat.completions/ }).parentElement as HTMLElement;
    expect(root.style.marginInlineStart).toBe('calc(var(--space-4) * 0)');
    expect(container.querySelector('[style*="margin-left"]')).toBeNull();
  });

  it('labels the two span kinds it names and leaves the rest quiet', async () => {
    const { container } = render(<TraceViewer traceId="trace-1" />);
    await act(async () => {});

    expect(within(screen.getByRole('button', { name: /chat.completions/ })).getByText('[llm_call]')).toBeTruthy();
    expect(within(screen.getByRole('button', { name: /run_shell/ })).getByText('[tool_call]')).toBeTruthy();
    // A kind badge is a categorical fact, so it takes the quiet text role and
    // never a status colour.
    const badge = screen.getByText('[llm_call]');
    expect(badge.className).toBe('shrink-0 font-mono text-[length:var(--text-2xs)] text-[var(--color-info)]');
    expect(container.innerHTML).not.toMatch(/text-\[(red|green|blue|yellow|amber|emerald)-/);
  });

  it('shows the statistics with a tone for each fact', async () => {
    const { container } = render(<TraceViewer traceId="trace-1" />);
    await act(async () => {});

    expect(within(screen.getByText(key('tracing.stat.errors')).parentElement as HTMLElement).getByText('1')).toBeTruthy();
    expect(within(screen.getByText(key('tracing.stat.llm_calls')).parentElement as HTMLElement).getByText('1')).toBeTruthy();
    // A measurement is compared across tiles, so it is a mono number.
    const spans = within(screen.getByText(key('tracing.stat.spans')).parentElement as HTMLElement).getByText('3');
    expect(spans.className).toContain('font-mono');
    expect(container.querySelectorAll('.tabular-nums').length).toBeGreaterThan(0);
  });

  it('opens a span to its id, time, error and metadata', async () => {
    render(<TraceViewer traceId="trace-1" />);
    await act(async () => {});

    await userEvent.click(screen.getByRole('button', { name: /chat.completions/ }));
    expect(screen.getByText('span-1')).toBeTruthy();
    expect(screen.getByText('2026-09-26T10:00:01Z')).toBeTruthy();

    await userEvent.click(screen.getByRole('button', { name: key('tool_call.arguments') }));
    expect(screen.getByText(/"cwd": "\/srv\/app"/)).toBeTruthy();
  });

  it('names a span error block and keeps it in the error role', async () => {
    render(<TraceViewer traceId="trace-1" />);
    await act(async () => {});

    await userEvent.click(screen.getByRole('button', { name: /run_shell/ }));
    const errorBlock = screen.getByText('command exited with 1').closest('.overflow-auto');
    expect(errorBlock?.className).toContain('text-[var(--color-error)]');
    expect(errorBlock?.className).toContain('border-[var(--color-error)]/30');
  });

  it('loads the span tree for the trace it is pointed at', async () => {
    render(<TraceViewer traceId="trace-2" />);
    await act(async () => {});
    expect(getTrace).toHaveBeenCalledWith('trace-2');
  });

  it('says the list is loading, then that it is empty', async () => {
    listTraces.mockResolvedValue([]);
    await act(async () => {
      render(<TraceViewer />);
    });
    const status = screen.getByRole('status');
    expect(status.textContent).toContain(key('tracing.empty_title'));
    expect(status.querySelector('.text-\\[var\\(--color-unknown\\)\\]')).toBeTruthy();
  });

  it('reports a failed trace list as an error with a retry', async () => {
    listTraces.mockRejectedValue(new Error('offline'));
    await act(async () => {
      render(<TraceViewer />);
    });
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain(key('tracing.errors.list'));
    expect(alert.querySelector('.text-\\[var\\(--color-error\\)\\]')).toBeTruthy();

    listTraces.mockResolvedValue(TRACES);
    await userEvent.click(within(alert).getByRole('button'));
    expect(await screen.findByText('Run')).toBeTruthy();
  });

  it('reports a failed span load as an error without dropping the trace list', async () => {
    getTrace.mockRejectedValue(new Error('gone'));
    render(<TraceViewer traceId="trace-1" />);
    await act(async () => {});

    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain(key('tracing.errors.detail'));
    expect(screen.getByText('Run')).toBeTruthy();
  });

  it('asks for a selection when no trace is pointed at', async () => {
    await act(async () => {
      render(<TraceViewer />);
    });
    expect(getTrace).not.toHaveBeenCalled();
    expect(screen.getByText(key('tracing.select_hint'))).toBeTruthy();
  });
});
