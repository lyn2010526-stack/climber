import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import { ExecutionTree, resolveNodeTone, type ExecutionNode } from './ExecutionTree';

afterEach(() => cleanup());

const tree: ExecutionNode[] = [
  {
    id: 'root',
    label: 'Agent run',
    status: 'running',
    children: [
      { id: 'plan', label: 'Plan', status: 'success', detail: '{"steps":3}' },
      {
        id: 'tool',
        label: 'run_shell',
        status: 'failed',
        children: [{ id: 'tool-retry', label: 'retry', status: 'pending' }],
      },
      { id: 'done', label: 'Summarize', status: 'completed' },
    ],
  },
];

describe('ExecutionTree', () => {
  it('renders a tree and expands every branch by default', () => {
    render(<ExecutionTree nodes={tree} />);
    const root = screen.getByRole('tree').querySelector('[data-node-id="root"]')!;
    expect(within(root as HTMLElement).getByText('Agent run')).toBeVisible();
    expect(screen.getByText('Plan')).toBeVisible();
    expect(screen.getByText('run_shell')).toBeVisible();
    expect(screen.getByText('retry')).toBeVisible();
    expect(screen.getByText('Summarize')).toBeVisible();
  });

  it('collapses and expands a parent without dropping its children', () => {
    render(<ExecutionTree nodes={tree} />);
    const expandButton = screen.getByRole('button', { name: /run_shell/ });
    expect(expandButton).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('retry')).toBeVisible();

    fireEvent.click(expandButton);
    expect(expandButton).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('retry')).not.toBeInTheDocument();
    // The parent summary stays put while collapsed.
    expect(within(expandButton).getByText('run_shell')).toBeVisible();

    fireEvent.click(expandButton);
    expect(screen.getByText('retry')).toBeVisible();
  });

  it('honours defaultExpandedIds instead of expanding everything', () => {
    render(<ExecutionTree nodes={tree} defaultExpandedIds={['root']} />);
    expect(screen.getByRole('button', { name: /run_shell/ })).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText('retry')).not.toBeInTheDocument();
    // A depth-one child with its own children is still reachable.
    expect(screen.getByText('Plan')).toBeVisible();
  });

  it('shows a node detail payload once its branch is open', () => {
    render(<ExecutionTree nodes={tree} />);
    expect(screen.getByText(/"steps":3/)).toBeVisible();
  });

  it('carries a distinct tone per status and an unknown fallback', () => {
    expect(resolveNodeTone('succeeded')).toBe('success');
    expect(resolveNodeTone('FAILED')).toBe('error');
    expect(resolveNodeTone('in_progress')).toBe('loading');
    expect(resolveNodeTone('paused')).toBe('warning');
    expect(resolveNodeTone('weird-new-state')).toBe('unknown');
    expect(resolveNodeTone(undefined)).toBeNull();
  });

  it('renders the empty state when there are no nodes', () => {
    render(<ExecutionTree nodes={[]} />);
    expect(screen.getByText(i18n.t('execution.empty', { defaultValue: 'No execution steps recorded.' }))).toBeVisible();
  });

  it('exposes each node status through the shared status vocabulary', () => {
    render(<ExecutionTree nodes={[{ id: 'only', label: 'Step', status: 'queued' }]} />);
    const node = screen.getByRole('tree').querySelector('[data-node-id="only"]')!;
    expect(node.getAttribute('data-status')).toBe('queued');
  });
});
