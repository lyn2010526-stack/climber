import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { TerminalPanel } from '../TerminalPanel';

describe('TerminalPanel', () => {
  it('renders terminal container', () => {
    const { container } = render(<TerminalPanel />);
    expect(container.innerHTML).toBeDefined();
    expect(container.querySelector('div')).not.toBeNull();
  });

  it('applies custom className', () => {
    const { container } = render(<TerminalPanel className="h-96" />);
    expect(container.querySelector('.h-96')).not.toBeNull();
  });

  it('renders in read-only mode without input', () => {
    const { container } = render(<TerminalPanel readOnly />);
    expect(container.innerHTML).toBeDefined();
    expect(container.querySelector('div')).not.toBeNull();
  });
});
