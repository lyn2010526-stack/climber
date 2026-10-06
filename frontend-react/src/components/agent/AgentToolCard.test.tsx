import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AgentToolCard } from './AgentToolCard';

describe('AgentToolCard', () => {
  it('shows the tool name, a status pill and the elapsed time in the header', () => {
    render(<AgentToolCard name="read_file" status="running" elapsedMs={1400} />);
    const card = screen.getByTestId('agent-tool-card');
    expect(card).toHaveAttribute('data-status', 'running');
    expect(screen.getByText('read_file')).toBeVisible();
    expect(screen.getByText('Running')).toBeVisible();
    expect(screen.getByText('1.4s')).toBeVisible();
  });

  it('keeps the body hidden until the header is activated', () => {
    render(<AgentToolCard name="web_search" status="success" input={{ q: 'jan' }} output="3 results" />);
    expect(screen.queryByText('Input')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /web_search/ }));
    expect(screen.getByText('Input')).toBeVisible();
    expect(screen.getByText('Output')).toBeVisible();
    expect(screen.getByText(/"q": "jan"/)).toBeVisible();
    expect(screen.getByText('3 results')).toBeVisible();
  });

  it('opens by default when the tool is awaiting approval', () => {
    render(<AgentToolCard name="container_exec" status="awaiting-approval" input={{ cmd: 'ls' }} />);
    expect(screen.getByTestId('agent-tool-approval')).toBeVisible();
    expect(screen.getByText(/"cmd": "ls"/)).toBeVisible();
  });

  it('fires approve and deny callbacks from the approval row', () => {
    const onApprove = vi.fn();
    const onDeny = vi.fn();
    render(<AgentToolCard name="write_file" status="awaiting-approval" onApprove={onApprove} onDeny={onDeny} />);
    const approval = screen.getByTestId('agent-tool-approval');
    fireEvent.click(within(approval).getByRole('button', { name: 'Deny' }));
    expect(onDeny).toHaveBeenCalledTimes(1);
    fireEvent.click(within(approval).getByRole('button', { name: 'Always allow' }));
    expect(onApprove).toHaveBeenCalledTimes(1);
  });

  it('renders an error payload on the error tone when the tool failed', () => {
    render(<AgentToolCard name="read_file" status="error" output="permission denied" defaultExpanded />);
    expect(screen.getByText('Failed')).toBeVisible();
    expect(screen.getByText('permission denied')).toBeVisible();
  });
});
