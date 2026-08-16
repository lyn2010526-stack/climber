import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThinkingDetails } from '../ThinkingDetails';

describe('ThinkingDetails', () => {
  it('renders thinking content when open', () => {
    render(
      <ThinkingDetails defaultOpen isComplete elapsedTime={1.5}>
        <span>Reasoning content</span>
      </ThinkingDetails>
    );
    expect(screen.getByText('Reasoning content')).toBeDefined();
  });

  it('renders completed thought label', () => {
    render(
      <ThinkingDetails isComplete elapsedTime={2.3}>
        Test
      </ThinkingDetails>
    );
    expect(screen.getByText(/思考完成 · 2\.3s/)).toBeDefined();
  });

  it('renders thinking label with timer', () => {
    render(
      <ThinkingDetails defaultOpen elapsedTime={0.5}>
        Test
      </ThinkingDetails>
    );
    const details = document.querySelector('details');
    expect(details).not.toBeNull();
    expect(details?.textContent).toContain('正在思考');
  });

  it('toggles on summary click', () => {
    render(
      <ThinkingDetails defaultOpen={false} isComplete elapsedTime={1.0}>
        Toggle me
      </ThinkingDetails>
    );
    const summary = screen.getByText(/思考完成 · 1\.0s/);
    fireEvent.click(summary);
    expect(screen.getByText('Toggle me')).toBeDefined();
  });
});
