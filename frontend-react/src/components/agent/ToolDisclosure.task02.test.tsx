import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../i18n';
import { ToolCallVisualization, type ToolCall } from './ToolCallVisualization';
import { FloatingPermissionDialog, extractApprovalTarget, type PermissionRequest } from './FloatingPermissionDialog';
import TraceViewer from '../tracing/TraceViewer';
import { normalizeToolStatus, resolveToolStatus } from './toolCallStatus';
import { TONE_GLYPH, TONE_TEXT } from '../ui/StatusIcon';
import { api } from '../../api';

vi.mock('../../api', () => ({ api: { listTraces: vi.fn(), getTrace: vi.fn() } }));

const baseCall: ToolCall = {
  id: 'call-1',
  name: 'run_command',
  arguments: { command: 'npm test' },
  result: 'Passed',
  status: 'success',
};

const baseRequest: PermissionRequest = {
  id: 'req-1',
  action: 'command',
  description: 'Run the selected command',
  details: 'npm test',
  severity: 'low',
  timestamp: 1,
};

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

describe('tool call disclosure defaults', () => {
  it('defaults every call to collapsed and hides payloads until the user asks', () => {
    render(<ToolCallVisualization calls={[baseCall, { ...baseCall, id: 'call-2', status: 'error', error: 'exit code 1' }]} />);
    const rows = screen.getAllByRole('button', { name: /run_command/ });
    expect(rows).toHaveLength(2);
    expect(rows.every(row => row.getAttribute('aria-expanded') === 'false')).toBe(true);
    expect(screen.queryByText(/"command"/)).not.toBeInTheDocument();
    // The collapsed summary keeps the whole error in the DOM; only the single
    // visual line is clipped, so nothing is discarded before the user expands.
    expect(screen.getByText('exit code 1')).toBeInTheDocument();
  });

  it('gives every lifecycle state a tone, an icon and matching wording', () => {
    for (const state of ['pending', 'running', 'success', 'error', 'cancelled', 'unknown'] as const) {
      const descriptor = resolveToolStatus(state, i18n.t);
      expect(descriptor.tone).toBeTruthy();
      // The glyph is the tone's, so a state cannot carry one icon and another
      // state the colour.
      expect(descriptor.icon).toBe(TONE_GLYPH[descriptor.tone]);
      expect(descriptor.className).toBe(TONE_TEXT[descriptor.tone]);
      expect(descriptor.label).toBe(i18n.t(`tool_call.status_${state}`));
    }
    render(<ToolCallVisualization calls={[{ ...baseCall, status: 'pending' }, { ...baseCall, id: 'c2', status: 'running' }, { ...baseCall, id: 'c3', status: 'error', error: 'boom' }]} />);
    expect(screen.getByText(i18n.t('tool_call.status_pending'))).toBeVisible();
    expect(screen.getByText(i18n.t('tool_call.status_running'))).toBeVisible();
    expect(screen.getByText(i18n.t('tool_call.status_error'))).toBeVisible();
  });

  it('keeps a stopped run apart from a failure and an unreported status apart from waiting', () => {
    // Cancelling is a user action, not a fault: it must not be reported red.
    expect(normalizeToolStatus('cancelled')).toBe('cancelled');
    expect(normalizeToolStatus('canceled')).toBe('cancelled');
    expect(normalizeToolStatus('aborted')).toBe('cancelled');
    expect(resolveToolStatus('cancelled', i18n.t).className).not.toContain('--color-error');
    // An unrecognised or missing status is unknown, never "still waiting".
    expect(normalizeToolStatus(undefined)).toBe('unknown');
    expect(normalizeToolStatus('something-new')).toBe('unknown');
    expect(normalizeToolStatus('completed')).toBe('success');
    expect(normalizeToolStatus('in_progress')).toBe('running');
    expect(normalizeToolStatus(true)).toBe('success');
    expect(normalizeToolStatus(false)).toBe('error');
  });

  it('renders a cancelled call and an unknown call without claiming a failure', () => {
    const { rerender } = render(<ToolCallVisualization calls={[{ ...baseCall, status: 'cancelled' }]} />);
    expect(screen.getByText(i18n.t('tool_call.status_cancelled'))).toBeVisible();
    expect(screen.queryByText(i18n.t('tool_call.status_error'))).not.toBeInTheDocument();

    rerender(<ToolCallVisualization calls={[{ ...baseCall, status: 'unknown' }]} />);
    expect(screen.getByText(i18n.t('tool_call.status_unknown'))).toBeVisible();
    expect(screen.queryByText(i18n.t('tool_call.status_pending'))).not.toBeInTheDocument();
  });
});

describe('payload reachability without truncation', () => {
  it('keeps long arguments, output and error fully in the DOM behind disclosures', () => {
    const long = 'x'.repeat(5000);
    render(<ToolCallVisualization calls={[{ ...baseCall, arguments: { body: long }, result: long, error: long, status: 'error', duration: 1500 }]} defaultExpanded />);
    fireEvent.click(screen.getByRole('button', { name: `${i18n.t('tool_call.arguments')} (1)` }));
    // Three independent blocks carry the full payload, so nothing is clipped.
    expect(screen.getAllByText(new RegExp(long.slice(0, 200)))).toHaveLength(3);
    expect(screen.getByText('1.5s')).toBeVisible();
    // Scrollable, not truncated: overflow is scrollable and no clamp utility cuts it.
    const blocks = screen.getAllByLabelText(i18n.t('tool_call.arguments'));
    expect(blocks[0]).toHaveClass('overflow-auto');
    expect(blocks[0]!.className).not.toMatch(/line-clamp/);
  });

  it('surfaces a full error even when the call never produced a result', () => {
    render(<ToolCallVisualization calls={[{ ...baseCall, status: 'error', result: undefined, error: 'EACCES: permission denied' }]} defaultExpanded />);
    expect(screen.getByText('EACCES: permission denied')).toBeVisible();
  });
});

describe('approval target visibility', () => {
  it('names the command from structured input and keeps extra details separate', () => {
    render(<FloatingPermissionDialog
      requests={[{ ...baseRequest, command: 'rm -rf /srv/data', details: 'exit 0' }]}
      onApprove={vi.fn()} onDeny={vi.fn()} onApproveAll={vi.fn()}
    />);
    expect(screen.getByText('rm -rf /srv/data')).toBeVisible();
    expect(screen.queryByText('exit 0')).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId('permission-details-toggle'));
    expect(screen.getByText('exit 0')).toBeVisible();
  });

  it('extracts the write path for file actions and the address for network actions', () => {
    render(<FloatingPermissionDialog
      requests={[
        { ...baseRequest, id: 'w', action: 'file_write', details: 'writing /etc/hosts', path: '/etc/hosts' },
        { ...baseRequest, id: 'n', action: 'network', details: 'GET', url: 'https://api.example.com/v1' },
        { ...baseRequest, id: 'm', action: 'mcp_tool', tool: 'github.create_issue' },
      ]}
      onApprove={vi.fn()} onDeny={vi.fn()} onApproveAll={vi.fn()}
    />);
    expect(screen.getByText('/etc/hosts')).toBeVisible();
    expect(screen.getByText('https://api.example.com/v1')).toBeVisible();
    expect(screen.getByText('github.create_issue')).toBeVisible();
  });

  it('falls back to a path-shaped details string when no structured field arrives', () => {
    render(<FloatingPermissionDialog
      requests={[{ ...baseRequest, action: 'file_delete', details: 'rm /var/lib/important.db', severity: 'low' }]}
      onApprove={vi.fn()} onDeny={vi.fn()} onApproveAll={vi.fn()}
    />);
    expect(screen.getByText('/var/lib/important.db')).toBeVisible();
    expect(extractApprovalTarget({ ...baseRequest, action: 'file_write', details: 'path: /srv/a/b.txt' })).toEqual({ kind: 'path', value: '/srv/a/b.txt' });
    expect(extractApprovalTarget({ ...baseRequest, details: 'curl -X POST https://x.dev' })).toEqual({ kind: 'command', value: 'curl -X POST https://x.dev' });
    expect(extractApprovalTarget({ ...baseRequest, details: undefined })).toBeUndefined();
  });

  it('blocks keyboard approval of a high-risk action until it is re-confirmed', async () => {
    const onApprove = vi.fn(() => Promise.resolve());
    render(<FloatingPermissionDialog
      requests={[{ ...baseRequest, severity: 'high', command: 'shutdown -h now' }]}
      onApprove={onApprove} onDeny={vi.fn()} onApproveAll={vi.fn()}
    />);
    await act(async () => { fireEvent.keyDown(document, { key: 'Enter', ctrlKey: true }); });
    expect(onApprove).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('checkbox'));
    await act(async () => { fireEvent.keyDown(document, { key: 'Enter', ctrlKey: true }); });
    expect(onApprove).toHaveBeenCalledExactlyOnceWith('req-1');
  });
});

describe('approval keyboard and retry guarantees', () => {
  it('approves and denies from the keyboard with the documented modifiers', async () => {
    const onApprove = vi.fn(() => Promise.resolve());
    const onDeny = vi.fn(() => Promise.resolve());
    const denied = render(<FloatingPermissionDialog requests={[baseRequest]} onApprove={onApprove} onDeny={onDeny} onApproveAll={vi.fn()} />);
    // Denial first: a decided request is gone, so the second decision needs a
    // request of its own rather than a re-enabled control.
    await act(async () => { fireEvent.keyDown(document, { key: 'Backspace', metaKey: true, shiftKey: true }); });
    expect(onDeny).toHaveBeenCalledExactlyOnceWith('req-1');
    expect(document.querySelector('section[data-approval-status]')).toBeNull();
    denied.unmount();

    render(<FloatingPermissionDialog requests={[baseRequest]} onApprove={onApprove} onDeny={onDeny} onApproveAll={vi.fn()} />);
    await act(async () => { fireEvent.keyDown(document, { key: 'Enter', metaKey: true }); });
    expect(onApprove).toHaveBeenCalledExactlyOnceWith('req-1');
    expect(document.querySelector('section[data-approval-status]')).toBeNull();
  });

  it('ignores the shortcut while typing and while an input holds focus', async () => {
    const onApprove = vi.fn(() => Promise.resolve());
    render(<FloatingPermissionDialog requests={[baseRequest]} onApprove={onApprove} onDeny={vi.fn()} onApproveAll={vi.fn()} />);
    const input = document.createElement('input');
    document.body.appendChild(input);
    await act(async () => { fireEvent.keyDown(input, { key: 'Enter', ctrlKey: true }); });
    await act(async () => { fireEvent.keyDown(document, { key: 'Enter', ctrlKey: true, altKey: true }); });
    expect(onApprove).not.toHaveBeenCalled();
    input.remove();
  });

  it('locks repeat submissions and preserves the command for retry after a failure', async () => {
    let fail!: (error: Error) => void;
    let calls = 0;
    const onApprove = vi.fn(() => {
      calls += 1;
      return calls === 1
        ? new Promise<void>((_, reject) => { fail = reject; })
        : Promise.resolve();
    });
    const { container } = render(<FloatingPermissionDialog
      requests={[{ ...baseRequest, command: 'terraform apply' }]}
      onApprove={onApprove} onDeny={vi.fn()} onApproveAll={vi.fn()}
    />);
    // Located by the declared shortcut so the assertion holds in every locale.
    const approve = container.querySelector<HTMLButtonElement>('[aria-keyshortcuts*="Enter"]')!;
    fireEvent.click(approve);
    expect(approve).toBeDisabled();
    fireEvent.click(approve);
    await act(async () => { fireEvent.keyDown(document, { key: 'Enter', ctrlKey: true }); });
    expect(onApprove).toHaveBeenCalledOnce();

    await act(async () => { fail(new Error('gateway timeout')); });
    expect(screen.getByRole('alert')).toHaveTextContent('gateway timeout');
    expect(screen.getByText('terraform apply')).toBeVisible();
    expect(approve).toBeEnabled();

    await act(async () => { fireEvent.click(approve); });
    expect(onApprove).toHaveBeenCalledTimes(2);
  });
});

describe('trace span disclosure', () => {
  const span = {
    id: 'span-1', trace_id: 'trace-1', parent_id: null, kind: 'tool_call', name: 'run_shell',
    status: 'error', duration_ms: 42, tokens_used: 0, model: null, tool_name: 'bash',
    error: 'command exited with status 2', started_at: '2026-01-01T00:00:00Z',
    metadata: '{"cwd":"/srv/app","argv":["ls","-la"]}',
  };

  it('collapses spans by default and reveals error and metadata on demand', async () => {
    vi.mocked(api.listTraces).mockResolvedValue([{ id: 'trace-1', kind: 'run', name: 'Run', started_at: '2026-01-01T00:00:00Z' }]);
    vi.mocked(api.getTrace).mockResolvedValue({ spans: [span], stats: null });
    render(<TraceViewer />);
    await waitFor(() => expect(screen.getByText('Run')).toBeInTheDocument());
    await act(async () => { fireEvent.click(screen.getByText('Run')); });
    await waitFor(() => expect(screen.getByText(/run_shell/)).toBeInTheDocument());

    const row = screen.getByRole('button', { name: /run_shell/ });
    expect(row).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('command exited with status 2')).not.toBeInTheDocument();
    expect(within(row).getByText(i18n.t('tool_call.status_error'))).toBeVisible();

    fireEvent.click(row);
    expect(row).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('command exited with status 2')).toBeVisible();
    expect(within(row).getByText('42ms')).toBeVisible();

    fireEvent.click(screen.getByRole('button', { name: i18n.t('tool_call.arguments') }));
    expect(screen.getByText(/"cwd": "\/srv\/app"/)).toBeVisible();
  });

  it('maps backend status spellings onto the shared status vocabulary', async () => {
    vi.mocked(api.listTraces).mockResolvedValue([{ id: 'trace-2', kind: 'run', name: 'Two', started_at: '2026-01-01T00:00:00Z' }]);
    vi.mocked(api.getTrace).mockResolvedValue({
      spans: [
        { ...span, id: 'a', status: 'completed', name: 'done_span' },
        { ...span, id: 'b', status: 'in_progress', name: 'live_span' },
      ],
      stats: null,
    });
    render(<TraceViewer />);
    await waitFor(() => expect(screen.getByText('Two')).toBeInTheDocument());
    await act(async () => { fireEvent.click(screen.getByText('Two')); });
    const done = await screen.findByRole('button', { name: /done_span/ });
    const live = screen.getByRole('button', { name: /live_span/ });
    expect(within(done).getByText(i18n.t('tool_call.status_success'))).toBeVisible();
    expect(within(live).getByText(i18n.t('tool_call.status_running'))).toBeVisible();
  });
});
