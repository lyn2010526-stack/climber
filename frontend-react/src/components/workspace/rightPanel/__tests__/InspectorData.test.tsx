import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { api } from '../../../../api';
import { ActivitySection } from '../sections/ActivitySection';
import { DagSection, TraceSection } from '../sections/ExecutionSection';

vi.mock('../../../../i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }));
vi.mock('../../../../api', () => ({
  api: { getSessionMessages: vi.fn(), listTraces: vi.fn(), getClusterStatus: vi.fn() },
}));

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(api.getClusterStatus).mockResolvedValue({ plan: [] });
});

describe('inspector data fidelity', () => {
  it('keeps tool details collapsed and never infers success or running from message presence', async () => {
    vi.mocked(api.getSessionMessages).mockResolvedValue([
      { id: 'm', role: 'assistant', content: null, tool_call_id: null, tool_name: null, created_at: '',
        tool_calls: [{ id: 'one', function: { name: 'edit', arguments: '{broken' } }, { id: 'two', name: 'read' }] },
      { id: 'r', role: 'tool', content: 'permission denied', tool_call_id: 'one', tool_name: 'edit', created_at: '', tool_calls: [] },
    ]);
    render(<ActivitySection sessionId="s1" />);
    const edit = await screen.findByRole('button', { name: 'edit' });
    expect(edit).toHaveAttribute('aria-expanded', 'false');
    expect(screen.getByText('permission denied')).toBeInTheDocument();
    expect(screen.queryByText('tool_call.status_success')).not.toBeInTheDocument();
    expect(screen.queryByText('tool_call.status_running')).not.toBeInTheDocument();
    fireEvent.click(edit);
    expect(screen.getByText('{broken')).toBeInTheDocument();
    expect(screen.getByText('permission denied')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'read' }));
    expect(screen.getByText('permission denied')).toBeInTheDocument();
    expect(screen.getAllByText('right_panel.summary.none')).toHaveLength(2);
  });

  it('reports the resolved tool call tally and drops it back to none when empty', async () => {
    const onCount = vi.fn();
    vi.mocked(api.getSessionMessages).mockResolvedValue([
      { id: 'm', role: 'assistant', content: null, tool_call_id: null, tool_name: null, created_at: '',
        tool_calls: [{ id: 'one', name: 'read' }, { id: 'two', name: 'grep' }] },
    ]);
    render(<ActivitySection sessionId="s1" onCount={onCount} />);
    await screen.findByRole('button', { name: 'read' });
    expect(onCount).toHaveBeenLastCalledWith(2);
  });

  it('shows request failure and supports retry', async () => {
    vi.mocked(api.getSessionMessages).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce([]);
    render(<ActivitySection sessionId="s1" />);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'right_panel.states.retry' }));
    expect(await screen.findByText('right_panel.states.empty_tools')).toBeInTheDocument();
  });

  it('hides missing and invalid trace metrics without inventing a call type', async () => {
    vi.mocked(api.listTraces).mockResolvedValue({ traces: [
      { id: 'one', name: 'Unknown metrics' },
      { id: 'two', name: 'Invalid metrics', duration: -1, tokens: Infinity },
    ] });
    render(<TraceSection />);
    await screen.findByText('Unknown metrics');
    expect(screen.queryByText(/right_panel.trace.duration/)).not.toBeInTheDocument();
    expect(screen.queryByText(/right_panel.trace.tokens/)).not.toBeInTheDocument();
    expect(screen.queryByText('LLM')).not.toBeInTheDocument();
  });

  it('names an unnamed trace step instead of substituting a placeholder label', async () => {
    vi.mocked(api.listTraces).mockResolvedValue({ traces: [{ id: 'one', name: '   ' }, { id: 'two' }] });
    render(<TraceSection />);
    await screen.findAllByText('right_panel.summary.none');
    expect(screen.getAllByText('right_panel.summary.none')).toHaveLength(2);
    expect(screen.queryByText('Unknown')).not.toBeInTheDocument();
  });

  it('tints a plan step only from a status its own payload reports', async () => {
    vi.mocked(api.getClusterStatus).mockResolvedValue({ plan: [
      { id: 'done', description: 'Settled', status: 'completed' },
      { id: 'live', description: 'In flight', status: 'running' },
      { id: 'odd', description: 'Unheard of', status: 'zzz' },
    ] });
    const { container } = render(<DagSection />);
    await screen.findByText('Settled');
    const markers = Array.from(container.querySelectorAll('span.rounded-full'));
    expect(markers[0]?.className).toContain('border-[var(--color-success)]');
    expect(markers[1]?.className).toContain('border-[var(--color-info)]');
    // An unrecognised status stays neutral rather than being guessed into a colour.
    expect(markers[2]?.className).toContain('border-[var(--color-border-strong)]');
  });

  it('reports no plan tally until entries resolve', async () => {
    const onCount = vi.fn();
    render(<DagSection onCount={onCount} />);
    await screen.findByText('right_panel.states.empty_dag');
    expect(onCount).toHaveBeenLastCalledWith(0);
  });
});
