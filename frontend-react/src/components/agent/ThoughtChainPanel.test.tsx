import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ThoughtChainPanel } from './ThoughtChainPanel';

describe('ThoughtChainPanel', () => {
  it('renders one numbered step per entry with its label and status', () => {
    render(
      <ThoughtChainPanel
        steps={[
          { id: 'a', label: 'Read the spec', status: 'success' },
          { id: 'b', label: 'Draft the change', status: 'running' },
          { id: 'c', label: 'Run tests', status: 'pending' },
        ]}
      />,
    );
    const chain = screen.getByTestId('thought-chain');
    expect(chain.tagName).toBe('OL');
    expect(screen.getByTestId('thought-step-a')).toHaveAttribute('data-status', 'success');
    expect(screen.getByTestId('thought-step-b')).toHaveAttribute('data-status', 'running');
    expect(screen.getByTestId('thought-step-c')).toHaveAttribute('data-status', 'pending');
    expect(chain).toHaveTextContent('1');
    expect(chain).toHaveTextContent('2');
    expect(chain).toHaveTextContent('3');
    expect(screen.getByText('Read the spec')).toBeVisible();
    expect(screen.getByText('Draft the change')).toBeVisible();
    expect(screen.getByText('Run tests')).toBeVisible();
  });

  it('carries an accessible status label for each step', () => {
    render(
      <ThoughtChainPanel steps={[{ id: 'x', label: 'Search', status: 'error' }]} />,
    );
    expect(screen.getByText('Failed')).toBeVisible();
  });

  it('renders nothing when there are no steps', () => {
    const { container } = render(<ThoughtChainPanel steps={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
